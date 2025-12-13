from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Teacher routes
    path('classroom/create/', views.create_classroom, name='create_classroom'),
    path('exam/create/<int:classroom_id>/', views.create_exam, name='create_exam'),
    path('question/add/<int:exam_id>/', views.add_question, name='add_question'),
    path('exam/launch/<int:exam_id>/', views.launch_exam, name='launch_exam'),
    path('submissions/<int:exam_id>/', views.view_submissions, name='view_submissions'),
    path('evaluate/<int:submission_id>/', views.evaluate_submission, name='evaluate_submission'),

    # Student routes
    path('classrooms/search/', views.search_classrooms, name='search_classrooms'),
    path('classroom/join/<int:classroom_id>/', views.join_classroom, name='join_classroom'),
    path('exam/take/<int:exam_id>/', views.take_exam, name='take_exam'),
    path('exam/submit/<int:submission_id>/', views.submit_exam, name='submit_exam'),
    path('results/<int:submission_id>/', views.view_result, name='view_result'),
]
