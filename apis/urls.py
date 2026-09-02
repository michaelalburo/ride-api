from rest_framework.routers import DefaultRouter

from rideflow.apps.rides.views import RideEventViewSet, RideViewSet
from rideflow.apps.users.views import UserViewSet

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register('rides', RideViewSet, basename='ride')
router.register('ride-events', RideEventViewSet, basename='rideevent')

urlpatterns = router.urls
