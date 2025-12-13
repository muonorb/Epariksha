# Register your models here.
from django.contrib import admin
from .models import Classroom, Exam, Question, Submission, Answer 

class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'status', 'evaluation_time_formatted', 'bert_time')
    readonly_fields = ('evaluation_time_formatted', 'bert_time')
    
admin.site.register(Classroom)
admin.site.register(Exam)
admin.site.register(Question)
admin.site.register(Submission)
admin.site.register(Answer)
