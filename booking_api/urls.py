from django.urls import path

from booking_api import views

urlpatterns = [
    path("", views.index, name="index"),
    path("load-data/", views.load_data_page, name="load-data"),
    path("api/schedule/", views.schedule_config, name="schedule-config"),
    path("api/bookings/", views.bookings, name="bookings"),
    path("api/bookings/<int:booking_id>/cancel/", views.cancel_booking_view, name="cancel-booking"),
    path("api/system-counts/", views.system_counts, name="system-counts"),
    path("api/supervisor-links/upload/", views.upload_supervisor_links, name="upload-supervisor-links"),
    path("api/supervisor-links/template/", views.download_template, name="download-template"),
    path("api/recommendations/", views.recommendations, name="recommendations"),
    path("api/supervisors/search/", views.search_supervisors, name="search-supervisors"),
    path("exportdata/", views.export_bookings, name="export-bookings"),
]
