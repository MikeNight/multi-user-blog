from urllib.parse import quote_plus

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import RedirectView
from django.utils import timezone

from comments.forms import CommentForm
from comments.models import Comment
from .forms import PostForm
from .models import Post

def list(request): #list itmes
	today = timezone.now().date()
	queryset_list = Post.objects.all().order_by("-timestamp", "-updated") #active()
	if request.user.is_staff or request.user.is_superuser:
		queryset_list = Post.objects.all()

	query = request.GET.get("q")
	if query:
		queryset_list = query_list.filter(
			Q(title__icontains=query) |
			Q(content__icontains=query) |
			Q(user__first_name__icontains=query) |
			Q(user__last_name____icontains=query)
			).distinct()

	paginator = Paginator(queryset_list, 10) # Show 25 contacts per page
	page_request_var = "page"
	page = request.GET.get(page_request_var)
	try:
		queryset = paginator.page(page)
	except PageNotAnInteger:
		# If page is not an integer, deliver first page.
		queryset = paginator.page(1)
	except EmptyPage:
		# If page is out of range (e.g. 9999), deliver last page of results.
		queryset = paginator.page(paginator.num_pages)
	context = {
		"page_request_var": page_request_var,
		"object_list": queryset,
		"title": "List",
		"today": today,
	}
	return render(request, 'posts.html', context)

def create(request):
	if not request.user.is_authenticated():
		raise Http404
	form = PostForm(request.POST or None, request.FILES or None)
	if form.is_valid():
		instance = form.save(commit=False)
		print(form.cleaned_data.get("title"))
		instance.user = request.user
		instance.save()
		# message success
		messages.success(request, "Successfully Created")
		return HttpResponseRedirect(instance.get_absolute_url())
	else:
		messages.error(request, "Not Successfully Created")
	context = {
		"form": form,
	}
	return render(request, 'post_form.html', context)

def detail(request, slug=None): #retrieve
	instance = get_object_or_404(Post, slug=slug)
	if instance.draft:
			if not request.user.is_authenticated:
				raise Http404
	share_string = quote_plus(instance.content)

	initial_data = {
			"content_type": instance.get_content_type,
			"object_id": instance.id
	}
	form = CommentForm(request.POST or None, initial=initial_data)
	if form.is_valid() and request.user.is_authenticated():
		c_type = form.cleaned_data.get("content_type")
		content_type = ContentType.objects.get(model=c_type)
		obj_id = form.cleaned_data.get('object_id')
		content_data = form.cleaned_data.get("content")
		parent_obj = None
		try:
			parent_id = int(request.POST.get("parent_id"))
		except:
			parent_id = None

		if parent_id:
			parent_qs = Comment.objects.filter(id=parent_id)
			if parent_qs.exists() and parent_qs.count() == 1:
				parent_obj = parent_qs.first()

		new_comment, created = Comment.objects.get_or_create(
							user = request.user,
							content_type = content_type,
							object_id = obj_id,
							content = content_data,
							parent = parent_obj,
						)
		return HttpResponseRedirect(new_comment.content_object.get_absolute_url())

	comments = instance.comments
	context = {
		"title": instance.title,
		"instance": instance,
		"share_string": share_string,
		"comments": comments,
		"comment_form":form,
	}
	return render(request, 'post_detail.html', context)

class PostLikeToggle(RedirectView):
	def get_redirect_url(self, *args, **kwargs):
		slug = self.kwargs.get("slug")
		print(slug)
		obj = get_object_or_404(Post, slug=slug)
		url_ = obj.get_absolute_url()
		user = self.request.user
		if user.is_authenticated():
			if user in obj.likes.all():
				obj.likes.remove(user)
			else:
				obj.likes.add(user)
		return url_

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions

class PostLikeAPIToggle(APIView):
	authentication_classes = (authentication.SessionAuthentication,)
	permission_classes = (permissions.IsAuthenticated,)

	def get(self, request, slug=None, format=None):
		#slug = self.kwargs.get("slug")
		obj = get_object_or_404(Post, slug=slug)
		url_ = obj.get_absolute_url()
		user = self.request.user
		updated = False
		liked = False
		if user.is_authenticated():
			if user in obj.likes.all():
				liked = False
				obj.likes.remove(user)
			else:
				liked = True
				obj.likes.add(user)
			updated = True
		data = {
			"updated": updated,
			"liked": liked
		}
		return Response(data)

def update(request, slug=None):
	if not request.user.is_staff or not request.user.is_superuser:
		raise Http404
	instance = get_object_or_404(Post, slug=slug)
	form = PostForm(request.POST or None, request.FILES or None, instance=instance)
	if form.is_valid():
		instance = form.save(commit=False)
		instance.save()
		# message success
		messages.success(request, "Saved")
		return HttpResponseRedirect(instance.get_absolute_url())
	context = {
		"title": instance.title,
		"instance": instance,
		"form":form,
	}
	return render(request, 'post_form.html', context)

def delete(request, slug=None):
	if not request.user.is_staff or not request.user.is_superuser:
		raise Http404
	instance = get_object_or_404(Post, slug=slug)
	instance.delete()
	messages.success(request, "Successfully Deleted")
	return redirect("posts:list")
