import csv
import os
import traceback
from datetime import datetime
from io import TextIOWrapper
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from background_task import background
from .models import Contacts
from .logic import Logic


def home(request):
    """homepage. basicaly it's currentcontacts"""
    return render(request, "importer/home.html")


def registeruser(request):
    """User Registration"""
    registration_html = 'importer/registeruser.html'
    if request.method == "GET":
        return render(request, registration_html, {'form': UserCreationForm()})
    else:
        if request.POST['password1'] == request.POST['password2']:
            # check if uname is email
            if '@' in request.POST['username']:
                # if passwords match trying to save user and redirecting him to currentcontacts
                try:
                    user = User.objects.create_user(
                        username=request.POST['username'],
                        password=request.POST['password1']
                    )
                    user.save()
                    login(request, user)
                    return redirect('currentcontacts')

                except IntegrityError:
                    msg = 'That username has been already been taken. Please choose a new username'
                    return render(request, registration_html, {'form': UserCreationForm(), 'error': msg})
            else:
                msg = 'Please use email as your username'
                return render(request, registration_html, {'form': UserCreationForm(), 'error': msg})

        else:
            msg = 'Passwords did not match'
            return render(request, registration_html, {'form': UserCreationForm(), 'error': msg})


def loginuser(request):
    """logins user in to system"""
    auth_html = 'importer/loginuser.html'
    if request.method == "GET":
        return render(request, auth_html, {'form': AuthenticationForm()})
    else:
        user = authenticate(
            request,
            username=request.POST['username'],
            password=request.POST['password']
        )
        if user is None:
            msg = 'Username and password did not match'
            return render(request, auth_html, {'form': AuthenticationForm(), 'error': msg})
        else:
            login(request, user)
            return redirect('contacts')


def logoutuser(request):
    """logs out user"""
    if request.method == "POST":
        logout(request)
        return redirect('home')


def cleartable(request):
    """clears table"""
    if request.method == "POST":
        Contacts.objects.all().delete()
    return redirect('contacts')

def start_background_task(request):
    """clears table"""
    if request.method == "POST":
        run_background_import()
    return redirect('contacts')


def setcolumns(request):
    return render(request, "importer/contacts.html")


def show_summary(init_size: int, rowcount: int, err: str):
    emsg = "Not all contacts from this file imported because they're already exist or incorrect fields format. " \
           " Please try to set columns order first"
    summary = f"{Contacts.objects.count() - init_size} out of {rowcount} contacts has been imported."
    if Contacts.objects.count() - init_size < rowcount:
        summary += emsg
    return summary + err


def csv_process(request):
    """main csv data import process"""
    summary = ""
    init_size = Contacts.objects.count()
    csv_file = TextIOWrapper(request.FILES["contacts_file"].file, encoding='utf-8')

    reader = csv.reader(csv_file)
    if request.GET.get('header', True):
        _ = next(reader)

    broken, rowcount = [], 0
    for row in reader:
        try:
            rowcount += 1
            broken, skip_1 = Logic.name_checker(request, row, broken)
            broken, skip_2 = Logic.check_empty(request, row, broken)
            if not skip_1 + skip_2:
                Contacts.objects.get_or_create(
                    Name=row[int(request.GET.get('name', '1')) - 1],
                    DOB=datetime.strptime(row[int(request.GET.get('dob', '2')) - 1], '%Y-%m-%d'),
                    Phone=row[int(request.GET.get('phone', '3')) - 1],
                    Address=row[int(request.GET.get('address', '4')) - 1],
                    CreditCard=row[int(request.GET.get('cc', '5')) - 1],
                    Franchise=Logic.select_franchise(),
                    Email=row[int(request.GET.get('email', '6')) - 1],
                )
        except Exception as ex:
            err = error_processor(ex)
            summary = show_summary(init_size, rowcount, err)
            continue
        summary = show_summary(init_size, rowcount, "")
    return broken, summary


def view_upload_contacts(request):
    """main page with contacts importer and paginated viewer"""
    # TO-DO "prerun save settings" button functionality
    summary = ""
    contacts_template = 'importer/contacts.html'
    if request.method == 'POST':
        try:
            broken, summary = csv_process(request)
        except Exception as ex:
            error_processor(ex)
            msg = 'Something went wrong or no file attached'
            return render(request, contacts_template, {'contacts': None, 'summary': msg})

    contacts_list = Contacts.objects.order_by("-Email")
    page = request.GET.get('page', 1)
    paginator = Paginator(contacts_list, 3)
    try:
        thecontacts = paginator.page(page)
    except PageNotAnInteger:
        thecontacts = paginator.page(1)
    except EmptyPage:
        thecontacts = paginator.page(paginator.num_pages)

    return render(request, contacts_template,  {'contacts': thecontacts, 'summary': summary})


def error_processor(ex: Exception) -> str:
    """error processor"""
    # TO-DO return message for log or add logging
    print("An exception of type {0} occurred. Arguments:\n{1!r}".format(type(ex).__name__, ex.args))
    msg = [item for item in traceback.format_exception(type(ex), ex, ex.__traceback__)]
    print(msg)
    return msg[-1]


def csv_background_process():
    """main csv data import process"""
    # TO-DO -
    summary = ""
    init_size = Contacts.objects.count()
    csv_file = open(os.getcwd() + "/sample_files/sample-1.csv")

    reader = csv.reader(csv_file)
    # TO-DO consider implementing header logic
    _ = next(reader)

    broken, rowcount = [], 0
    for row in reader:
        try:
            rowcount += 1
            Contacts.objects.get_or_create(
                Name=row[0],
                DOB=datetime.strptime(row[1], '%Y-%m-%d'),
                Phone=row[2],
                Address=row[3],
                CreditCard=row[4],
                Franchise=Logic.select_franchise(),
                Email=row[5],
            )
        except Exception as ex:
            err = error_processor(ex)
            summary = show_summary(init_size, rowcount, err)
            continue
        summary = show_summary(init_size, rowcount, "")
    csv_file.close()
    return broken, summary


@background(schedule=5)
def run_background_import():
    csv_background_process()
