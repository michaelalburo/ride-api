from django.contrib import admin

from .models import Ride, RideEvent


class RideEventInline(admin.TabularInline):
    model = RideEvent
    extra = 0


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'rider', 'driver', 'pickup_time')
    list_filter = ('status',)
    search_fields = ('rider__email', 'driver__email')
    inlines = [RideEventInline]


@admin.register(RideEvent)
class RideEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'ride', 'description', 'created_at')
    list_filter = ('description',)
