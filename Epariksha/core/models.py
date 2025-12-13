from django.db import models
from django.contrib.auth.models import User

class Classroom(models.Model):
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='classrooms')

    def __str__(self):
        return f"{self.name} (Teacher: {self.teacher.username})"


class Exam(models.Model):
    name = models.CharField(max_length=100)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    launched = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} (Classroom: {self.classroom.name})"

class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    text = models.TextField()
    model_answer = models.TextField()
    marks = models.PositiveIntegerField()
    def __str__(self):
        return f"Q: {self.text[:50]}... (Exam: {self.exam.name})"

class Submission(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    submitted = models.BooleanField(default=False)
    status = models.CharField(max_length=20, default='not_started')  
    evaluation_time = models.IntegerField(null=True, blank=True)
    bert_time = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Submission by {self.student.username} for {self.exam.name}"

     

class Answer(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    descriptive_answer = models.TextField(blank=True)
    code_answer = models.TextField(blank=True)
    student_marks = models.FloatField(blank=True, null=True)
    teacher_feedback = models.TextField(blank=True)
    bert_marks = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"Answer to '{self.question.text[:40]}...' by {self.submission.student.username}"
