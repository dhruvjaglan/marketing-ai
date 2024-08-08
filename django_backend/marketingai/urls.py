from django.urls import path

from marketingai.views import CompanyMarketSegmentListAPIView, create_company_user, create_new_marketing_segment, create_user_view, email_sequence_view, generate_mail_sequence, get_detailed_description, get_final_filters, search, search_results_view, segment_view, send_message, get_mails, create_home_view, sequence_result_view, sequence_view, update_description, get_case_study, create_mail_sequence, get_email_sequences, create_personalisation, get_all_sequence_task

### create_mail_sequence, get_email_sequences, create_personalisation, get_all_squence_task

urlpatterns = [
    path('create_user/', create_company_user),
    path('company_detail/<int:pk>/', get_detailed_description),
    path('get_case_study/<int:pk>/', get_case_study),
    path('new_segment/', create_new_marketing_segment),
    path('update_company_description/', update_description),
    path('send_message/<int:pk>/', send_message),
    path('get_filters/<int:pk>/', get_final_filters),
    path('search/<int:pk>/', search),
    path('create_mail_sequence/<int:pk>/', create_mail_sequence),
    path('get_email_sequences/<int:pk>/', get_email_sequences),
    path('create_personalisation/<int:pk>/', create_personalisation),
    path('get_all_sequence_task/<int:pk>/', get_all_sequence_task),
    path('generate_sequence/<int:pk>/', generate_mail_sequence),
    path('get_started/', create_user_view, name='create_user'),
    path('home/', create_home_view),
    path('sequences/', email_sequence_view),
    path('sequence/<int:sequence_id>/', sequence_view),
    path('sequence/result/<int:sequence_id>/', sequence_result_view),
    path('market_segment/<int:company_id>/', CompanyMarketSegmentListAPIView.as_view()),
    path('segment/<int:segment_id>/', segment_view, name='segment_chat'),
    path('segment/result/<int:segment_id>/', search_results_view, name='segment_chat')
]