from django.urls import path

from core import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('new-transaction/', views.new_trasaction, name='new_transaction'),
    path('transaction/create/', views.create_transaction, name='criar_transacao'),

    path("historical/", views.historical, name="historical"),
    path("transaction/<int:id>/edit/", views.edit_transaction, name="edit_transaction"),
    path("transaction/<int:id>/delete/", views.delete_transaction, name="delete_transaction"),

    path('reports/', views.reports, name='reports'),
    path('cards/', views.cards, name='cards'),
]
