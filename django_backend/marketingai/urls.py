from django.urls import path

from marketingai.views import CompanyMarketSegmentListAPIView, create_company_user, create_new_marketing_segment, create_user_view, get_detailed_description, search, search_results_view, segment_view, send_message, get_mails, create_home_view, update_description


urlpatterns = [
    path('create_user/', create_company_user),
    path('company_detail/<int:pk>/', get_detailed_description),
    path('new_segment/', create_new_marketing_segment),
    path('update_company_description/', update_description),
    path('send_message/<int:pk>/', send_message),
    path('search/<int:pk>/', search),
    path('get_mails/<int:pk>/', get_mails),
    path('get_started/', create_user_view, name='create_user'),
    path('home/', create_home_view),
    path('market_segment/<int:company_id>/', CompanyMarketSegmentListAPIView.as_view()),
    path('segment/<int:segment_id>/', segment_view, name='segment_chat'),
    path('segment/result/<int:segment_id>/', search_results_view, name='segment_chat')
]