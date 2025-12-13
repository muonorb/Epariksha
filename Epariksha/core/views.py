from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from accounts.models import Profile
from .models import Classroom, Exam, Question, Submission, Answer
from django.contrib.auth.models import User
import language_tool_python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from transformers import pipeline
import subprocess
import tempfile
from sentence_transformers import util
from django.contrib import messages
import time
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from transformers import pipeline
from sentence_transformers import SentenceTransformer


# Load the summarization pipeline once (specify model explicitly)
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# Load sentence transformer once for sentence embeddings
bert_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')


@login_required
def dashboard_view(request):
    profile = request.user.profile
    if profile.user_type == 'teacher':
        classrooms = Classroom.objects.filter(teacher=request.user)
        return render(request, 'core/teacher_dashboard.html', {'classrooms': classrooms})
    else:
        submissions = Submission.objects.filter(student=request.user)
        return render(request, 'core/student_dashboard.html', {'submissions': submissions})

@login_required
def create_classroom(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        Classroom.objects.create(name=name, teacher=request.user)
        return redirect('dashboard')
    return render(request, 'core/create_classroom.html')

@login_required
def create_exam(request, classroom_id):
    classroom = get_object_or_404(Classroom, id=classroom_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        Exam.objects.create(name=name, classroom=classroom)
        return redirect('dashboard')
    return render(request, 'core/create_exam.html', {'classroom': classroom})

@login_required
def add_question(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    if request.method == 'POST':
        Question.objects.create(
            exam=exam,
            text=request.POST.get('text'),
            model_answer=request.POST.get('model_answer'),
            marks=request.POST.get('marks')
        )
        return redirect('add_question', exam_id=exam.id)
    questions = Question.objects.filter(exam=exam)
    return render(request, 'core/add_question.html', {'exam': exam, 'questions': questions})

@login_required
def launch_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    exam.launched = True
    exam.save()
    return redirect('dashboard')

@login_required
def search_classrooms(request):
    classrooms = Classroom.objects.all()
    return render(request, 'core/search_classrooms.html', {'classrooms': classrooms})

@login_required
def join_classroom(request, classroom_id):
    classroom = get_object_or_404(Classroom, id=classroom_id)
    exams = Exam.objects.filter(classroom=classroom)

    for exam in exams:
        Submission.objects.get_or_create(
            exam=exam,
            student=request.user,
            defaults={'status': 'not_started', 'submitted': False}
        )

    return redirect('dashboard')

@login_required
def take_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    submission, created = Submission.objects.get_or_create(exam=exam, student=request.user, defaults={'status': 'not_started'})

    if request.method == 'POST':
        # save answers
        for question in exam.question_set.all():
            Answer.objects.create(
                submission=submission,
                question=question,
                descriptive_answer=request.POST.get(f'answer_{question.id}'),
                code_answer=request.POST.get(f'code_{question.id}')
            )
        submission.submitted = True
        submission.status = 'awaiting_evaluation'  
        submission.save()
        return redirect('dashboard')
    
    total_max_marks = sum(q.marks for q in exam.question_set.all())
    
    return render(request, 'core/take_exam.html', {
        'exam': exam,
        'total_max_marks': total_max_marks,
        })

@login_required
def submit_exam(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    submission.submitted = True
    submission.save()
    return redirect('dashboard')

@login_required
def view_submissions(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    submissions = Submission.objects.filter(exam=exam)

    # ✅ Pre-format evaluation time here
    for submission in submissions:
        if submission.evaluation_time is not None:
            mins, secs = divmod(submission.evaluation_time, 60)
            submission.evaluation_time_formatted = f"{mins}m {secs}s"
        else:
            submission.evaluation_time_formatted = "Not Evaluated Yet"

        if submission.bert_time is not None:
            submission.bert_time_formatted = f"{submission.bert_time:} milsec"

        else:
            submission.bert_time_formatted = "N/A"

        total_marks = sum(a.student_marks or 0 for a in submission.answers.all())
        submission.total_marks = total_marks
    
    total_max_marks = sum(q.marks for q in exam.question_set.all())

    return render(request, 'core/view_submissions.html', {
        'exam': exam,
        'submissions': submissions,
        'total_max_marks': total_max_marks,
    })



@login_required
def evaluate_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    answers = submission.answers.all()

    # ✅ Start timer on GET
    if request.method == "GET":
        request.session['eval_start_time'] = time.time()

    tool = language_tool_python.LanguageTool('en-US')

    answers_data = [] 

    for answer in answers:
        #Separate descriptive and code parts
        student_desc = (answer.descriptive_answer or "").strip()  
        student_code = (answer.code_answer or "").strip()  
        model_text = (answer.question.model_answer or "").strip()

        bert_start_time = time.perf_counter()
        # Determine case type
        if student_desc and student_code:
            student_text_combined = student_desc + "\n\n" + student_code
            case_type = "both"
        elif student_desc:
            student_text_combined = student_desc
            case_type = "descriptive"
        elif student_code:
            student_text_combined = student_code
            case_type = "code_only"
        else:
            student_text_combined = ""
            case_type = "empty"


        # Tokenize student and model answers to word sets (case insensitive)
        model_words = set(model_text.lower().split())
        student_words = student_text_combined.lower().split()

        # Count how many student words appear in model answer words
        matching_word_count = sum(1 for w in student_words if w in model_words)

        # Calculate word similarity as matching_word_count / model_word_count * 100
        model_word_count = len(model_words) if model_words else 1  # avoid zero-divide
        word_count = (matching_word_count / model_word_count) * 100

        
        # Count lines in model and student answers
        model_line_count = len(model_text.splitlines())
        student_line_count = len(student_text_combined.splitlines())

        # Avoid division by zero
        if model_line_count == 0:
            line_count = 100.0 if student_line_count > 0 else 0.0
        else:
            line_count = (student_line_count / model_line_count) * 100
            if line_count > 100:
                line_count = 100.0


        # Initialize default values for analytics
        cosine_sim = "N/A"      
        summary = "N/A"         
        grammar_errors = "N/A"  

        # Compute analytics only if NOT code-only
        if case_type in ["both", "descriptive"]:  
            # Grammar check
            matches = tool.check(student_desc)  
            grammar_errors = len(matches)

            # Cosine similarity (TF-IDF)
            vectorizer = TfidfVectorizer().fit([model_text, student_text_combined])
            vectors = vectorizer.transform([model_text, student_text_combined])
            cosine_sim = cosine_similarity(vectors[0], vectors[1])[0][0]
            cosine_sim = round(cosine_sim * 100, 2)

            # --- Summarization ---
            input_len = len(student_desc.split())
            max_len = min(70, input_len + 10) if input_len > 0 else 30
            min_len = min(15, max_len)
            try:
                summary_list = summarizer(student_desc, max_length=max_len, min_length=min_len, do_sample=False, early_stopping=True)
                summary = summary_list[0]['summary_text']

                if "CNN.com will feature iReporter photos" in summary:
                    summary = "Summary not available."

            except Exception:
                summary = "Summary not available."


        # Code execution MAC
        # code_result = ''
        # code_error = ''
        # if student_code:
        #     try:
        #         with tempfile.NamedTemporaryFile(suffix='.c', delete=True) as source_file:
        #             source_file.write(student_code.encode())
        #             source_file.flush()

        #             compile_proc = subprocess.run(
        #                 ['gcc', source_file.name, '-o', '/tmp/a.out'],
        #                 capture_output=True,
        #                 text=True,
        #                 timeout=5
        #             )
        #             if compile_proc.returncode != 0:
        #                 code_error = compile_proc.stderr
        #             else:
        #                 run_proc = subprocess.run(
        #                     ['/tmp/a.out'],
        #                     capture_output=True,
        #                     text=True,
        #                     timeout=5
        #                 )
        #                 code_result = run_proc.stdout
        #                 code_error += run_proc.stderr
        #     except Exception as e:
        #         code_error = str(e)

        
        # Code execution Windows
        code_result = ''
        code_error = ''
        
        if student_code:
            try:
                with tempfile.NamedTemporaryFile(suffix=".c", delete=False) as source_file:
                    source_file.write(student_code.encode())
                    source_file.flush()
                    c_path = source_file.name
        
                exe_path = c_path.replace(".c", ".exe")
        
                compile_proc = subprocess.run(
                    ["gcc", c_path, "-o", exe_path],
                    capture_output=True,
                    text=True,
                    timeout=7,
                    shell=True    
                )
        
                if compile_proc.returncode != 0:
                    code_error = compile_proc.stderr
        
                else:
                    run_proc = subprocess.run(
                        [exe_path],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        shell=True   
                    )
        
                    code_result = run_proc.stdout
                    code_error = run_proc.stderr
        
            except Exception as e:
                code_error = str(e)
        
            finally:
                try:
                    os.remove(c_path)
                except:
                    pass
                try:
                    os.remove(exe_path)
                except:
                    pass


        # BERT similarity scoring 
        bert_start_time = time.perf_counter()
        similarity_score = 0
        if student_text_combined.strip() and model_text.strip():
            emb1 = bert_model.encode(model_text, convert_to_tensor=True)
            emb2 = bert_model.encode(student_text_combined, convert_to_tensor=True)
            similarity_score = util.cos_sim(emb1, emb2).item()

        bert_end_time = time.perf_counter()
        bert_predict_time = (bert_end_time - bert_start_time) * 1000

        # Scale to question marks
        bert_marks = round(similarity_score * answer.question.marks, 2)

        # Append data
        answers_data.append({
            'answer': answer,
            'case_type': case_type,  
            'word_count': word_count,
            'line_count': line_count,
            'grammar_errors': grammar_errors,
            'cosine_similarity': cosine_sim,
            'summary': summary,
            'code_answer': student_code,
            'code_result': code_result,
            'code_error': code_error,
            'bert_marks': bert_marks,
            'max_marks': answer.question.marks,
            'bert_time': bert_predict_time,
        })

    # ====== POST: Save marks & calculate evaluation time ======
    if request.method == 'POST':
        has_warning = False
        for item in answers_data:
            ans = item['answer']
            teacher_marks = request.POST.get(f'marks_{ans.id}')
            teacher_marks = float(teacher_marks) if teacher_marks else 0
            bert_marks = item['bert_marks']

            allowed_diff = 0.2 * ans.question.marks
            if abs(teacher_marks - bert_marks) > allowed_diff:
                messages.warning(
                    request,
                    f"Marks for Question '{ans.question.text[:40]}...' "
                    f"deviate significantly from BERT predicted ({bert_marks})."
                )
                has_warning = True

            ans.student_marks = teacher_marks

            # --- Feedback fix ---
            feedback_option = request.POST.get(f'feedback_select_{ans.id}', '').strip()
            custom_feedback = request.POST.get(f'feedback_{ans.id}', '').strip()

            if feedback_option == 'custom':
                final_feedback = custom_feedback
            else:
                final_feedback = feedback_option

            ans.teacher_feedback = final_feedback
            # ---------------------

            ans.bert_marks = bert_marks
            ans.save()

        print("POST DATA:", request.POST)


        # Calculate duration
        start_time = request.session.get('eval_start_time')
        if start_time:
            duration_seconds = int(time.time() - start_time)
            submission.evaluation_time = duration_seconds
            request.session.pop('eval_start_time', None)

        total_bert_time = 0
        for item in answers_data:
            if 'bert_time' in item:
                total_bert_time += item['bert_time']

        submission.bert_time = total_bert_time 

        submission.status = 'evaluated'
        submission.save()

        return redirect('view_submissions', exam_id=submission.exam.id)

    return render(request, 'core/evaluate_submission.html', {
        'submission': submission,
        'answers_data': answers_data,
    })


@login_required
def view_result(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    answers = submission.answers.all()
    total_marks = sum(a.student_marks or 0 for a in answers) 
    total_max_marks = sum(q.marks for q in submission.exam.question_set.all())
    return render(request, 'core/view_result.html', {
        'submission': submission,
        'answers': answers,
        'total_marks': total_marks,
        'total_max_marks': total_max_marks,
    })
