
from django.urls import path
from . import views

app_name = 'administration'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),


    path('users/', views.UserListView.as_view(), name='user_list'),

    path('users/<int:pk>/update/', views.UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/detail/', views.UserDetailView.as_view(), name='user_detail_admin'),



    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/update/', views.ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),


    path('product-categories/', views.ProductCategoryListView.as_view(), name='productcategory_list'),
    path('product-categories/create/', views.ProductCategoryCreateView.as_view(), name='productcategory_create'),
    path('product-categories/<int:pk>/update/', views.ProductCategoryUpdateView.as_view(), name='productcategory_update'),
    path('product-categories/<int:pk>/delete/', views.ProductCategoryDeleteView.as_view(), name='productcategory_delete'),



    path('product-brands/', views.ProductBrandListView.as_view(), name='productbrand_list'),
    path('product-brands/create/', views.ProductBrandCreateView.as_view(), name='productbrand_create'),
    path('product-brands/<int:pk>/update/', views.ProductBrandUpdateView.as_view(), name='productbrand_update'),
    path('product-brands/<int:pk>/delete/', views.ProductBrandDeleteView.as_view(), name='productbrand_delete'),



    path('product-reviews/', views.ProductReviewListView.as_view(), name='productreview_list'),
    path('product-reviews/<int:pk>/update/', views.ProductReviewUpdateView.as_view(), name='productreview_update'),
    path('product-reviews/<int:pk>/delete/', views.ProductReviewDeleteView.as_view(), name='productreview_delete'),


    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', views.OrderDetailView.as_view(), name='order_detail_admin'),
    path('orders/<int:pk>/update/', views.OrderUpdateView.as_view(), name='order_update'),



    path('listings/', views.ListingListView.as_view(), name='listing_list'),
    path('listings/create/', views.ListingCreateView.as_view(), name='listing_create'),
    path('listings/<int:pk>/update/', views.ListingUpdateView.as_view(), name='listing_update'),
    path('listings/<int:pk>/delete/', views.ListingDeleteView.as_view(), name='listing_delete'),


    path('marketplace-categories/', views.MarketplaceCategoryListView.as_view(), name='marketplacecategory_list'),
    path('marketplace-categories/create/', views.MarketplaceCategoryCreateView.as_view(), name='marketplacecategory_create'),
    path('marketplace-categories/<int:pk>/update/', views.MarketplaceCategoryUpdateView.as_view(), name='marketplacecategory_update'),
    path('marketplace-categories/<int:pk>/delete/', views.MarketplaceCategoryDeleteView.as_view(), name='marketplacecategory_delete'),


    path('forum-topics/', views.ForumUserPostListView.as_view(), name='forumuserpost_list'),

    path('forum-topics/<int:pk>/update/', views.ForumUserPostUpdateView.as_view(), name='forumuserpost_update'),
    path('forum-topics/<int:pk>/delete/', views.ForumUserPostDeleteView.as_view(), name='forumuserpost_delete'),



    path('forum-categories/', views.ForumCategoryListView.as_view(), name='forumcategory_list'),
    path('forum-categories/create/', views.ForumCategoryCreateView.as_view(), name='forumcategory_create'),
    path('forum-categories/<int:pk>/update/', views.ForumCategoryUpdateView.as_view(), name='forumcategory_update'),
    path('forum-categories/<int:pk>/delete/', views.ForumCategoryDeleteView.as_view(), name='forumcategory_delete'),



    path('forum-answers/', views.ForumAnswerListView.as_view(), name='forumanswer_list'),
    path('forum-answers/<int:pk>/update/', views.ForumAnswerUpdateView.as_view(), name='forumanswer_update'),
    path('forum-answers/<int:pk>/delete/', views.ForumAnswerDeleteView.as_view(), name='forumanswer_delete'),


    path('charging-stations/', views.ChargingStationListView.as_view(), name='chargingstation_list'),
    path('charging-stations/create/', views.ChargingStationCreateView.as_view(), name='chargingstation_create'),
    path('charging-stations/<int:pk>/update/', views.ChargingStationUpdateView.as_view(), name='chargingstation_update'),
    path('charging-stations/<int:pk>/delete/', views.ChargingStationDeleteView.as_view(), name='chargingstation_delete'),


    path('station-bookings/', views.StationBookingListView.as_view(), name='stationbooking_list'),
    path('station-bookings/<int:pk>/update/', views.StationBookingUpdateView.as_view(), name='stationbooking_update'),
    path('station-bookings/<int:pk>/delete/', views.StationBookingDeleteView.as_view(), name='stationbooking_delete'),


    path('electric-vehicles/', views.ElectricVehicleListView.as_view(), name='electricvehicle_list'),
    path('electric-vehicles/create/', views.ElectricVehicleCreateView.as_view(), name='electricvehicle_create'),
    path('electric-vehicles/<int:pk>/update/', views.ElectricVehicleUpdateView.as_view(), name='electricvehicle_update'),
    path('electric-vehicles/<int:pk>/delete/', views.ElectricVehicleDeleteView.as_view(), name='electricvehicle_delete'),



    path('vehicle-reports/', views.VehicleReportListView.as_view(), name='vehiclereport_list'),
    path('vehicle-reports/<int:pk>/', views.VehicleReportDetailView.as_view(), name='vehiclereport_detail_admin'),
    path('vehicle-reports/<int:pk>/delete/', views.VehicleReportDeleteView.as_view(), name='vehiclereport_delete'),


    path('newsletter-subscribers/', views.NewsletterSubscriberListView.as_view(), name='newslettersubscriber_list'),
    path('newsletter-subscribers/<int:pk>/delete/', views.NewsletterSubscriberDeleteView.as_view(), name='newslettersubscriber_delete'),
]