from couchdbkit.ext.django.forms import DocumentForm
from django.forms.fields import CharField
from django.forms.widgets import HiddenInput
from django.shortcuts import render_to_response
from django.template import RequestContext

from models import Post, Comment


class PostForm(DocumentForm):
    
    class Meta:
        document = Post
        
class CommentForm(DocumentForm):

    post = CharField(widget=HiddenInput(), required=False)

    class Meta:
        document = Comment

def home(request):
    post = None
    form = PostForm(request.POST or None)
    
    if request.POST:
        if form.is_valid():
            post = form.save()

    posts = Post.view('blog_app/all_posts', descending=True)
    
    return render_to_response("home.html", {
        "form": form,
        "post": post,
        "posts": posts
    }, context_instance=RequestContext(request))

def view_post(request, post_id):
    post = Post.get(post_id)
    form = CommentForm(request.POST or None)

    if request.POST:
        if form.is_valid():
            form.cleaned_data['post'] = post_id
            form.save()

    comments = Comment.view('blog_app/commets_by_post', key=post_id)
    
    return render_to_response("post_details.html", {
        "form": form,
        "post": post,
        "comments": comments
    }, context_instance=RequestContext(request))

def edit_post(request, post_id):
    post = Post.get(post_id)
    form = PostForm(request.POST or None, instance=post)
    
    if form.is_valid():
        post = form.save()
    
    return render_to_response("post_edit.html", {
        "form": form,
        "post": post
    }, context_instance=RequestContext(request))