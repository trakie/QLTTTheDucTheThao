from django.http import HttpResponseForbidden

# def admin_trainer_required(view_func):
#     def wrapper(request, *args, **kwargs):
#         if not request.user.is_authenticated:
#             return HttpResponseForbidden()
#         if request.user.role in ['admin', 'trainer']:
#             return view_func(request, *args, **kwargs)
#         return HttpResponseForbidden()
#     return wrapper

def admin_trainer_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        if request.user.role in ['admin', 'trainer']:
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden()
    return wrapper