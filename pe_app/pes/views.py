import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q, Value
from django.db.models.functions import Concat
from django.core.paginator import Paginator
from . import dao
from .models import Class, Trainer, Enrollment, Payment, ClassSchedule, UserProfile, Post
import logging
from .decorators import admin_trainer_required, admin_staff_required
from .forms import PostForm

logger = logging.getLogger(__name__)


# Create your views here.
def home(request):
    # Lấy parameters từ URL
    search_kw = request.GET.get('kw')
    class_type = request.GET.get('class_type')

    # Lấy queryset ban đầu
    classes = dao.get_all_classes()
    trainers = dao.get_all_trainers()

    # Filter theo tên
    if search_kw:
        classes = classes.filter(name__icontains=search_kw)

    # Filter theo loại lớp
    if class_type:
        classes = classes.filter(class_type=class_type)

    context = {
        'classes': classes,
        'trainers': trainers,
        'class_types': Class.CLASS_TYPES,
    }

    return render(request, 'pes/home.html', context)


@login_required
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


@login_required
def payment(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)

    # Kiểm tra trạng thái thanh toán trước
    if enrollment.payment_status:
        return render(request, 'pes/payment.html', {
            'enrollment': enrollment,
            'payment_completed': True,
            'error': 'Đơn đăng ký này đã được thanh toán trước đó!'
        })

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
        enrollment.status = 'active'
        enrollment.save()

        return redirect('payment_success')

    return render(request, 'pes/payment.html', {'enrollment': enrollment, 'payment_methods': Payment.PAYMENT_METHODS})


@login_required
def payment_success(request):
    return render(request, 'pes/payment_success.html')


@login_required
def profile(request, pk):
    profile_user = get_object_or_404(UserProfile, pk=pk)

    # Lấy tất cả enrollment của user và related data
    enrollments = Enrollment.objects.filter(member=profile_user).select_related('class_enrolled')

    # Phân loại enrollment
    completed_enrollments = enrollments.filter(status='completed').order_by('-completion_date')
    active_enrollments = enrollments.filter(status='active').order_by('-enrollment_date')
    pending_payment_enrollments = enrollments.filter(status='pending', payment_status=False).order_by(
        '-enrollment_date')

    context = {
        'profile_user': profile_user,
        'completed_enrollments': completed_enrollments,
        'active_enrollments': active_enrollments,
        'pending_payment_enrollments': pending_payment_enrollments
    }

    return render(request, 'pes/profile.html', context)


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


@login_required
@require_http_methods(["POST"])
def update_enrollment(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)

    # Kiểm tra quyền HLV
    if request.user != enrollment.class_enrolled.trainer.user:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    try:
        # Đọc và validate dữ liệu
        data = json.loads(request.body)
        new_status = data.get('status')

        # Kiểm tra trạng thái hợp lệ
        if new_status not in dict(Enrollment.STATUS_CHOICES):
            return JsonResponse({'error': 'Trạng thái không hợp lệ'}, status=400)

        # Kiểm tra trạng thái không thay đổi
        if enrollment.status == new_status:
            return JsonResponse({'warning': 'Trạng thái không thay đổi'}, status=200)

        # Xử lý ngày hoàn thành
        if new_status == 'completed':
            enrollment.completion_date = timezone.now()
        elif enrollment.status == 'completed' and new_status != 'completed':
            enrollment.completion_date = None

        # Cập nhật và lưu
        enrollment.status = new_status
        enrollment.save()

        return JsonResponse({
            'success': True,
            'new_status': enrollment.get_status_display(),
            'completion_date': enrollment.completion_date.strftime(
                "%d/%m/%Y %H:%M") if enrollment.completion_date else None
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_avatar(request):
    try:
        user = request.user

        if 'avatar' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'Vui lòng chọn ảnh'
            }, status=400)

        old_avatar = user.avatar
        old_public_id = old_avatar.public_id if old_avatar else None

        user.avatar = request.FILES['avatar']
        user.save()

        response_data = {
            'success': True,
            'new_url': user.avatar.url,
            'public_id': user.avatar.public_id
        }
        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Avatar update error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Lỗi server: ' + str(e)
        }, status=500)


@login_required
@admin_staff_required
def receipts(request):
    search_kw = request.GET.get('kw')
    class_kw = request.GET.get('class_kw')

    payments = dao.get_all_payment()

    if search_kw:
        payments = payments.annotate(  # Thêm trường ảo full_name
            full_name=Concat('user__first_name', Value(' '), 'user__last_name')
        ).filter(
            Q(user__username__icontains=search_kw) |
            Q(user__email__icontains=search_kw) |
            Q(full_name__icontains=search_kw) |
            Q(user__first_name__icontains=search_kw) |
            Q(user__last_name__icontains=search_kw)
        )

    if class_kw:
        payments = payments.filter(enrollment__class_enrolled__name__icontains=class_kw)

    return render(request, 'pes/receipts.html', context={'payments': payments})


@login_required
@admin_staff_required
def class_schedule(request):
    # Lấy parameters từ URL
    search_kw = request.GET.get('kw')
    class_type = request.GET.get('class_type')

    # Lấy danh sách ClassSchedule đã sắp xếp và kèm thông tin Schedule
    ordered_schedules = ClassSchedule.objects.select_related('schedule').order_by(
        'schedule__day_of_week',
        'schedule__time_block'
    )

    # Lấy tất cả lớp học kèm thông tin HLV và lịch đã sắp xếp
    classes = Class.objects.select_related('trainer').prefetch_related(
        Prefetch('schedules', queryset=ordered_schedules)
    ).all()

    # Filter theo tên
    if search_kw:
        classes = classes.filter(name__icontains=search_kw)

    # Filter theo loại lớp
    if class_type:
        classes = classes.filter(class_type=class_type)

    paginator = Paginator(classes, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'classes': classes,
        'class_types': Class.CLASS_TYPES,
        'page_obj': page_obj,
    }

    return render(request, 'pes/class_schedule.html', context)


@login_required
def news(request):
    # Lấy parameters từ URL
    search_kw = request.GET.get('kw')
    news_type = request.GET.get('news_type')

    # Lấy tất cả bài viết và sắp xếp theo thời gian tạo
    post_list = Post.objects.all()

    # Filter theo nội dung
    if search_kw:
        post_list = post_list.filter(
            Q(title__icontains=search_kw) |
            Q(content__icontains=search_kw)
        )

    # Filter theo loại tin
    if news_type:
        post_list = post_list.filter(category=news_type)

    # Phân trang với 5 bài viết mỗi trang
    paginator = Paginator(post_list, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'pes/news.html', {
        'page_obj': page_obj,
        'categories': Post.CATEGORIES  # Thêm categories vào context nếu cần filter
    })


@login_required
def news_detail(request, pk):
    post = get_object_or_404(Post.objects.select_related('author'), pk=pk)
    return render(request, 'pes/news_detail.html', {'post': post})


@login_required
@admin_trainer_required
@require_http_methods(['GET', 'POST'])
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('news_detail', pk=post.pk)
    else:
        form = PostForm()

    return render(request, 'pes/post_form.html', {
        'form': form,
        'title': 'Tạo bài viết mới'
    })


@login_required
@admin_trainer_required
@require_http_methods(['GET', 'POST'])
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk)

    if request.user.role == 'trainer' and post.author != request.user:
        return HttpResponseForbidden("Bạn không có quyền chỉnh sửa bài viết này")

    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return redirect('news_detail', pk=post.pk)
    else:
        form = PostForm(instance=post)

    return render(request, 'pes/post_form.html', {
        'form': form,
        'title': 'Chỉnh sửa bài viết'
    })


@login_required
@admin_trainer_required
@require_http_methods(['POST'])
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk)

    # Kiểm tra quyền trainer
    if request.user.role == 'trainer' and post.author != request.user:
        return HttpResponseForbidden("Bạn không có quyền xóa bài viết này")

    post.delete()
    return redirect('news')