import json

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from . import dao
from .models import Class, Trainer, Enrollment, Payment, ClassSchedule, UserProfile
from .forms import EnrollmentForm


# Create your views here.
def home(request):
    classes = dao.get_all_classes()
    trainers = dao.get_all_trainers()
    return render(request, 'pes/home.html', {'classes': classes, 'trainers': trainers})


def enroll(request, pk):
    class_obj = get_object_or_404(Class, pk=pk)

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')

        # Check for existing non-completed enrollments
        existing_enrollment = Enrollment.objects.filter(
            member=request.user,
            class_enrolled=class_obj
        ).exclude(status='completed').first()

        if existing_enrollment:
            return render(request, 'pes/enroll.html', {
                'class_obj': class_obj,
                'error': f'Bạn đã đăng ký lớp này rồi! Trạng thái: {existing_enrollment.get_status_display()}'
            })

        # Rest of your existing code for schedule selection
        try:
            schedule_id = int(request.POST.get('schedule'))
            class_schedule = ClassSchedule.objects.get(
                lop=class_obj,
                schedule__id=schedule_id
            )
            schedule = class_schedule.schedule
        except (ValueError, ClassSchedule.DoesNotExist):
            return render(request, 'pes/enroll.html', {
                'class_obj': class_obj,
                'error': 'Lịch học không hợp lệ!'
            })

        # Create new enrollment
        enrollment = Enrollment.objects.create(
            member=request.user,
            class_enrolled=class_obj,
            schedule_selected=schedule,
            status='pending',
            payment_status=False
        )

        return redirect('payment', enrollment_id=enrollment.id)

    # GET request handling remains the same
    class_schedules = ClassSchedule.objects.filter(lop=class_obj)
    return render(request, 'pes/enroll.html', {
        'class_obj': class_obj,
        'class_schedules': class_schedules
    })


def class_detail(request, pk):
    class_obj = get_object_or_404(Class, pk=pk)
    return render(request, 'pes/class_detail.html', {'class_obj': class_obj})


def trainer_detail(request, pk):
    trainer_obj = get_object_or_404(Trainer, pk=pk)
    return render(request, 'pes/trainer_detail.html', {'trainer_obj': trainer_obj})


def payment(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id', '').strip()

        # Handle different payment methods
        if payment_method == 'cash':
            transaction_id = f"CASH-{enrollment.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        elif not transaction_id:
            return render(request, 'pes/payment.html', {
                'enrollment': enrollment,
                'error': 'Vui lòng nhập mã giao dịch!'
            })

        # Create payment record
        Payment.objects.create(
            user=request.user,
            amount=enrollment.class_enrolled.price,
            payment_method=payment_method,
            transaction_id=transaction_id,
            enrollment=enrollment
        )

        # Update enrollment status
        enrollment.payment_status = True
        enrollment.save()

        return redirect('payment_success')

    return render(request, 'pes/payment.html', {'enrollment': enrollment})


def payment_success(request):
    return render(request, 'pes/payment_success.html')


def profile(request, pk):
    user_obj = get_object_or_404(UserProfile, pk=pk)
    return render(request, 'pes/profile.html', {'user_obj': user_obj})


def get_class_members(request, class_id):
    class_obj = get_object_or_404(Class, id=class_id)
    enrollments = Enrollment.objects.filter(
        class_enrolled=class_obj,
        status__in=['active', 'pending']  # Lấy cả học viên đang chờ xử lý
    ).select_related('member')

    return render(request, 'pes/partials/class_members.html', {
        'enrollments': enrollments,
        'class_obj': class_obj
    })


@require_http_methods(["POST"])
def update_enrollment(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)

    # Kiểm tra quyền: Chỉ HLV của lớp mới được cập nhật
    if request.user != enrollment.class_enrolled.trainer.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

        # Đọc dữ liệu JSON
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if enrollment.status == new_status:
        return JsonResponse({
            'warning': 'Trạng thái không thay đổi'
        }, status=200)

    new_status = json.loads(request.body).get('status')
    if new_status not in dict(Enrollment.STATUS_CHOICES).keys():
        return JsonResponse({'error': 'Invalid status'}, status=400)

    enrollment.status = new_status
    enrollment.save()

    return JsonResponse({
        'success': True,
        'new_status': enrollment.get_status_display()
    })
