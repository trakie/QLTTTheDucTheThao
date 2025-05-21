from django.shortcuts import render
from django.http import HttpResponse
from . import dao


# Create your views here.
def home(request):
    classes = dao.get_all_classes()
    return render(request, 'pes/home.html', {'classes': classes})


def enroll(request):
    return render(request, 'pes/enroll.html')