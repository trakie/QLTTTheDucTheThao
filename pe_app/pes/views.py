from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from . import dao
from .models import Class, Trainer


# Create your views here.
def home(request):
    classes = dao.get_all_classes()
    trainers = dao.get_all_trainers()
    return render(request, 'pes/home.html', {'classes': classes, 'trainers': trainers})


def enroll(request, pk):
    class_obj = get_object_or_404(Class, pk=pk)
    return render(request, 'pes/enroll.html', {'class_obj': class_obj})


def class_detail(request, pk):
    class_obj = get_object_or_404(Class, pk=pk)
    return render(request, 'pes/class_detail.html', {'class_obj': class_obj})


def trainer_detail(request, pk):
    trainer_obj = get_object_or_404(Trainer, pk=pk)
    return render(request, 'pes/trainer_detail.html', {'trainer_obj': trainer_obj})
