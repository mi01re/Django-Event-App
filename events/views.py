from django.shortcuts import render, redirect
import calendar
from calendar import HTMLCalendar
from datetime import datetime
from django.http import HttpResponseRedirect, HttpResponse, FileResponse
from .models import Event, Venue
from .forms import VenueForm, EventForm, EventFormAdmin
import csv
import io
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.models import User

#Show Event
def show_event(request, event_id):
    event = Event.objects.get(pk=event_id)
    return render(request, 'events/show_event.html', {
        "event" : event
    })
#Show Events in a Venue

def venue_events(request, venue_id):
    # Grab the venue
    venue = Venue.objects.get(id=venue_id)
    # Grab the events from that venue
    events = venue.event_set.all()
    if events:
        return render(request, 'events/venue_events.html', {
        "events" : events
    })
    else:
        messages.success(request, ("That Venue has no Events at this Time!"))
        return redirect('admin_approval')

#Create Admin Event Approval Page
def admin_approval(request):
    #Get Venues
    venue_list = Venue.objects.all()

    #Get Counts
    event_count = Event.objects.all().count()
    venue_count = Venue.objects.all().count()
    user_count = User.objects.all().count()

    event_list = Event.objects.all().order_by('-event_date')
    if request.user.is_superuser:
        if request.method == "POST":
            id_list = request.POST.getlist('boxes')
            #uncheck all events
            event_list.update(approved=False)
            #update database
            for x in id_list:
                Event.objects.filter(pk=int(x)).update(approved=True)

            messages.success(request, ("Event List Approval hast been updates!"))
            return redirect('list-events')

        else:
            return render(request, 'events/admin_approval.html', {"event_list" : event_list, "event_count" : event_count, "venue_count" : venue_count, "user_count" : user_count, "venue_list" : venue_list})
    else:
        messages.success(request, ("You aren't authorized to view this page!"))
        return redirect('home')




#Create My Events Page
def my_events(request):
    if request.user.is_authenticated:
        me = request.user.id
        events = Event.objects.filter(attendees=me)
        return render(request, 'events/my_events.html', {"events" : events })
    else:
        messages.success(request, ("You aren't authorized to view this page!"))
        return redirect('home')

#Generate PDF of Venues
def venue_pdf(request):
    #Create Bytestream buffer
    buf = io.BytesIO()
    #Create Canvas
    c = canvas.Canvas(buf, pagesize=letter, bottomup=0)
    #Create a text object
    textob = c.beginText()
    textob.setTextOrigin(inch, inch)
    textob.setFont("Helvetica", 14)

    venues = Venue.objects.all()
    lines = []
    for venue in venues:
        lines.append(venue.name)
        lines.append(venue.address)
        lines.append(venue.zip_code)
        lines.append(venue.phone)
        lines.append(venue.web)
        lines.append(venue.email_address)
        lines.append("")

    for line in lines:
        textob.textLine(line)

    #Finish up
    c.drawText(textob)
    c.showPage()
    c.save()
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename='venue.pdf')

def venue_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=venues.csv'

    #create a csv writer
    writer = csv.writer(response)

    #Designate the Model
    venues = Venue.objects.all()

    #Add column heading to csv file
    writer.writerow(['Venue Name', 'Address', 'Zip Code', 'Phone', 'Website', 'Email Address'])

    #Loop through and output
    for venue in venues:
        writer.writerow([venue.name, venue.address, venue.zip_code, venue.phone, venue.web, venue.email_address])

    return response



#Generate TextFile Venue List
def venue_text(request):
    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename=venues.txt'
    #Designate the Model
    venues = Venue.objects.all()

    #Create blank list
    lines = []

    #Loop through and output
    for venue in venues:
        lines.append(f'{venue.name}\n{venue.address}\n{venue.zip_code}\n{venue.phone}\n{venue.web}\n{venue.email_address}\n\n\n')

    #Write to TextFile
    response.writelines(lines)
    return response

def delete_venue(request, venue_id):
    venue = Venue.objects.get(pk=venue_id)
    venue.delete()
    return redirect('list-venues')

def delete_event(request, event_id):
    event = Event.objects.get(pk=event_id)
    if request.user == event.manager:
        event.delete()
        messages.success(request, ("Event Deleted!"))
        return redirect('list-events')
    else:
                messages.success(request, ("You aren't Authorized to Delete this Event!"))
    return redirect('list-events')

def update_event(request, event_id):
    event = Event.objects.get(pk=event_id)
    if request.user.is_superuser:
        form = EventFormAdmin(request.POST or None, instance=event)
    else:
        form = EventForm(request.POST or None, instance=event)
    if form.is_valid():
        form.save()
        return redirect('list-events')
    return render(request, 'events/update_event.html', {'event' : event, 'form' : form})

def add_event(request):
    submitted = False
    if request.method == "POST":
        if request.user.is_superuser:
            form = EventFormAdmin(request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect('/add_event?submitted=True')
        else:
            form = EventForm(request.POST)
            if form.is_valid():
                event = form.save(commit=False)
                event.manager = request.user #logged in user id
                event.save()
                #form.save()
                return HttpResponseRedirect('/add_event?submitted=True')
    else:
        #just going to the page, not submitting
        if request.user.is_superuser:
            form = EventFormAdmin
        else:
            form = EventForm
        if 'submitted' in request.GET:
            submitted = True
    return render(request, 'events/add_event.html', {'form' : form, 'submitted':submitted})

def update_venue(request, venue_id):
    venue = Venue.objects.get(pk=venue_id)
    form = VenueForm(request.POST or None, request.FILES or None, instance=venue)
    if form.is_valid():
        form.save()
        return redirect('list-venues')
    return render(request, 'events/update_venue.html', {'venue' : venue, 'form' : form})

def search_venues(request):
    if request.method == "POST":
        searched = request.POST['searched']
        venues = Venue.objects.filter(name__contains=searched)
        return render(request, 'events/search_venues.html', {'searched' : searched, 'venues' : venues})
    else:
        return render(request, 'events/search_venues.html', {})

def search_events(request):
    if request.method == "POST":
        searched = request.POST['searched']
        events = Event.objects.filter(name__contains=searched)
        return render(request, 'events/search_events.html', {'searched' : searched, 'events' : events})
    else:
        return render(request, 'events/search_events.html', {})

def show_venue(request, venue_id):
    venue = Venue.objects.get(pk=venue_id)
    venue_owner = User.objects.get(pk=venue.owner)
    # Grab the events from that venue
    events = venue.event_set.all()
    return render(request, 'events/show_venue.html', {'venue' : venue, 'venue_owner' : venue_owner, 'events' : events })

def list_venues(request):
    venue_list = Venue.objects.all()

    #Set up Pagination
    p = Paginator(Venue.objects.all(), 10)
    page = request.GET.get('page')
    venues = p.get_page(page)
    #count number of pages using length of sting instead of integer
    nums = "a" * venues.paginator.num_pages
    return render(request, 'events/venue.html', {'venue_list' : venue_list, 'venues' : venues, 'nums' : nums})

def add_venue(request):
    submitted = False
    if request.method == "POST":
        form = VenueForm(request.POST, request.FILES)
        if form.is_valid():
            venue = form.save(commit=False)
            venue.owner = request.user.id #logged in user id
            venue.save()
            #form.save()
            return HttpResponseRedirect('/add_venue?submitted=True')
    else:
        form = VenueForm
        if 'submitted' in request.GET:
            submitted = True
    return render(request, 'events/add_venue.html', {'form' : form, 'submitted':submitted})

def all_events(request):
    event_list = Event.objects.all().order_by('-event_date')
    return render(request, 'events/event_list.html', {'event_list' : event_list})

def home(request, year=datetime.now().year, month=datetime.now().strftime('%B')):
    #Convert month from name to number
    month = month.capitalize()
    month_number = list(calendar.month_name).index(month)
    month_number = int(month_number)

    #Create calendar
    cal = HTMLCalendar().formatmonth(year, month_number)

    #Query The Events Model for Dates
    event_list = Event.objects.filter(
        event_date__year = year,
        event_date__month = month_number,
        )

    return render(request, 'events/home.html', {
        "year" : year,
        "month" : month,
        "month_number" : month_number,
        "cal" : cal,
        "event_list" : event_list,
        })

