from django.contrib.auth import login, logout, authenticate, _get_backends
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Max
from django.http import (HttpResponseRedirect, HttpResponseBadRequest,
    JsonResponse, HttpResponseForbidden)
from django.shortcuts import render, get_object_or_404

from ISS import utils, forms
from ISS.models import *


def forum_index(request):
    forums = Forum.objects.all().order_by('priority')
    ctx = {
        'forums': [utils.ForumFascet(f, request) for f in forums]
    }

    return render(request, 'forum_index.html', ctx)

def thread_index(request, forum_id):
    forum = get_object_or_404(Forum, pk=forum_id)
    threads = forum.thread_set.order_by('-last_update')
    threads_per_page = utils.get_config('threads_per_forum_page')
    paginator = utils.MappingPaginator(threads, threads_per_page)

    paginator.install_map_func(lambda t: utils.ThreadFascet(t, request))

    page = utils.page_by_request(paginator, request)

    ctx = {
        'forum': forum,
        'threads': page
    }

    if request.user.is_authenticated():
        forum.mark_read(request.user)

    return render(request, 'thread_index.html', ctx)

def thread(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    posts = thread.post_set.order_by('created')
    posts_per_page = utils.get_config('posts_per_thread_page')
    paginator = Paginator(posts, posts_per_page)
    reply_form = forms.NewPostForm(author=request.user,
                                   initial={ 'thread': thread })

    page = utils.page_by_request(paginator, request)

    ctx = {
        'thread': thread,
        'posts': page,
        'reply_form': reply_form
    }

    response = render(request, 'thread.html', ctx)

    # Update thread flag
    if request.user.is_authenticated():
        thread.mark_read(request.user, page[-1])

    return response

def posts_by_user(request, user_id):
    poster = get_object_or_404(Poster, pk=user_id)
    posts = (poster.post_set
        .order_by('-created')
        .select_related('thread'))
    posts_per_page = utils.get_config('general_items_per_page')
    paginator = Paginator(posts, posts_per_page)

    page = utils.page_by_request(paginator, request)

    ctx = {
        'poster': poster,
        'posts': page
    }

    return render(request, 'posts_by_user.html', ctx)

def thanked_posts(request, user_id):
    poster = get_object_or_404(Poster, pk=user_id)
    posts = (Post.objects.filter(
        id__in=poster.post_set
            .filter(thanks__isnull=False)
            .order_by('-thanks__given')
        )
        .distinct()
        .select_related('thread'))

    posts = (poster.post_set
        .filter(thanks__isnull=False)
        .annotate(Max('thanks__given'))
        .order_by('-thanks__given__max'))

    posts_per_page = utils.get_config('general_items_per_page')
    paginator = Paginator(posts, posts_per_page)

    page = utils.page_by_request(paginator, request)

    ctx = {
        'poster': poster,
        'posts': page
    }

    return render(request, 'thanked_posts.html', ctx)

def latest_threads(request):
    threads = Thread.objects.all().order_by('-last_update')
    threads_per_page = utils.get_config('threads_per_forum_page')
    paginator = utils.MappingPaginator(threads, threads_per_page)

    paginator.install_map_func(lambda t: utils.ThreadFascet(t, request))

    page = utils.page_by_request(paginator, request)

    ctx = {
        'threads': page
    }

    return render(request, 'latest_threads.html', ctx)

def user_list(request):
    posters = Poster.objects.all().order_by('username')
    posters_per_page = 20
    pagniator = Paginator(posters, posters_per_page)

    page = utils.page_by_request(posters, posters_per_page)

    ctx = {
        'posters': page
    }

    return render(request, 'user_list.html', ctx)

def search(request):
    q = request.GET.get('q', None)

    if not q:
        return render(request, 'search_results.html', {})

    #sql = ('SELECT content FROM "%s" WHERE to_tsvector(\'english\', content) '
    #    '@@ to_tsquery(\'english\', %%s);') % (Post._meta.db_table,)
    #qs = Post.objects.raw(sql, (terms,))

    terms = ' & '.join(q.split(' '))
    qs = Post.objects.filter(content__tsmatch=terms)

    posts_per_page = utils.get_config('general_items_per_page')

    paginator = Paginator(qs, posts_per_page)

    page = utils.page_by_request(paginator, request)

    ctx = {
        'q': q,
        'posts': page
    }

    return render(request, 'search_results.html', ctx)

class UserProfile(utils.MethodSplitView):
    def GET(self, request, user_id):
        poster = get_object_or_404(Poster, pk=user_id)

        ctx = {
            'poster': poster
        }

        if poster.pk == request.user.pk:
            ctx['settings_form'] = forms.UserSettingsForm(initial={
                'email': request.user.email,
                'allow_js': request.user.allow_js,
                'allow_avatars': request.user.allow_avatars,
                'allow_image_embed': request.user.allow_image_embed,
                'timezone': request.user.timezone})

        return render(request, 'user_profile.html', ctx)

    def POST(self, request, user_id):
        poster = get_object_or_404(Poster, pk=user_id)

        if poster.pk != request.user.pk:
            raise PermissionDenied()

        form = forms.UserSettingsForm(request.POST)

        if form.is_valid():
            form.save(poster)
            return HttpResponseRedirect(poster.get_url())

        else:
            ctx = {
                'poster': poster,
                'settings_form': form
            }

            return render(request, 'user_profile.html', ctx)

class NewThread(utils.MethodSplitView):
    login_required = True
    active_required = True

    def GET(self, request, forum_id):
        forum = get_object_or_404(Forum, pk=forum_id)
        form = forms.NewThreadForm(initial={ 'forum': forum })
        
        ctx = {
            'forum': forum,
            'form': form
        }

        return render(request, 'new_thread.html', ctx)

    def POST(self, request, forum_id):
        forum = get_object_or_404(Forum, pk=forum_id)
        form = forms.NewThreadForm(request.POST)

        if form.is_valid():
            thread = form.save(request.user)
            return HttpResponseRedirect(thread.get_url())

        else:
            ctx = {
                'forum': forum,
                'form': form
            }

            return render(request, 'new_thread.html', ctx)

class NewReply(utils.MethodSplitView):
    login_required = True
    active_required = True

    def GET(self, request, thread_id):
        thread = get_object_or_404(Thread, pk=thread_id)
        form_initials = { 'thread': thread }
        author = request.user

        # Fetch BBCode for a quote in this response
        quoted_post_pk = request.GET.get('quote', None)
        if quoted_post_pk:
            try:
                quoted_post = Post.objects.get(pk=quoted_post_pk)
                form_initials['content'] = quoted_post.quote_content()

            except Post.DoesNotExist:
                pass

        form = forms.NewPostForm(author=author, initial=form_initials)
        
        ctx = {
            'thread': thread,
            'form': form
        }

        return render(request, 'new_post.html', ctx)

    def POST(self, request, thread_id):
        thread = get_object_or_404(Thread, pk=thread_id)
        author = request.user
        form = forms.NewPostForm(request.POST, author=author)

        if form.is_valid():
            post = form.save()
            return HttpResponseRedirect(post.get_url())

        else:
            ctx = {
                'thread': thread,
                'form': form
            }

            return render(request, 'new_post.html', ctx)

class EditPost(utils.MethodSplitView):
    login_required = True
    active_required = True
    
    def GET(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        form_initials = { 'content': post.content, 'post': post }

        if (not request.user == post.author) and (not request.user.is_staff):
            raise PermissionDenied()

        form = forms.EditPostForm(initial=form_initials)
        ctx = {
            'form': form,
            'post': post
        }

        return render(request, 'edit_post.html', ctx)

    def POST(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)

        if (not request.user == post.author) and (not request.user.is_staff):
            raise PermissionDenied()

        form = forms.EditPostForm(request.POST)

        if not form.is_valid():
            ctx = {
                'form': form,
                'post': post
            }

            return render(request, 'edit_post.html', ctx)

        form.save(editor=request.user)
        return HttpResponseRedirect(post.get_url())

def assume_identity(request, user_id):
    if not request.user.is_authenticated() or not request.user.is_admin:
        raise PermissionDenied()

    if not request.method == 'POST':
        return HttpResponseBadRequest('Method not supported.')

    target_user = get_object_or_404(Poster, pk=user_id)
    next_url = request.POST.get('next', '/')

    logout(request)
    login(request, target_user)

    return HttpResponseRedirect(next_url)

class GetQuote(utils.MethodSplitView):
    def GET(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        BBC = post.quote_content()

        return JsonResponse({
            'content': BBC
        })

class LoginUser(utils.MethodSplitView):
    def GET(self, request):
        form = forms.ISSAuthenticationForm()
        ctx = {'form': form}
        return render(request, 'login.html', ctx)

    def POST(self, request):
        logout(request)
        if request.POST:
            form = forms.ISSAuthenticationForm(data=request.POST, request=request)

            if form.is_valid():
                login(request, form.user_cache)
                next_url = request.POST.get('next', '/')
                return HttpResponseRedirect(next_url)

            else:
                ctx = {'form': form}
                return render(request, 'login.html', ctx)

class LogoutUser(utils.MethodSplitView):
    def POST(self, request):
        logout(request)

        next_url = request.POST.get('next', '/')
        return HttpResponseRedirect(next_url)

class RegisterUser(utils.MethodSplitView):
    def GET(self, request):
        form = forms.RegistrationForm()
        ctx = {'form': form}

        return render(request, 'register.html', ctx)

    def POST(self, request):
        form = forms.RegistrationForm(request.POST)

        if form.is_valid():
            poster = form.save(commit=True)

            # Ceremoniously call authenticate so login will succeed
            poster = authenticate(username = form.cleaned_data['username'],
                                  password = form.cleaned_data['password1'])
            login(request, poster)
            return HttpResponseRedirect('/')

        else:
            ctx = { 'form': form }

            return render(request, 'register.html', ctx)


class ThankPost(utils.MethodSplitView):
    require_login = True
    active_required = True

    def POST(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        thanks = Thanks(post=post, thanker=request.user, thankee=post.author)

        try:
            thanks.save()
        except IntegrityError:
            pass

        if request.is_ajax():
            return utils.render_mixed_mode(
                request,
                (('thanksBlock', 'thanks_block.html', {'post': post}),
                 ('postControls', 'post_controls.html', {'post': post})),
                additional={'status': 'SUCCESS'})
        else:
            return HttpResponseRedirect(post.get_url())

class UnthankPost(utils.MethodSplitView):
    require_login = True
    active_required = True

    def POST(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        thanks = get_object_or_404(Thanks, post=post, thanker=request.user)

        thanks.delete()

        if request.is_ajax():
            return utils.render_mixed_mode(
                request,
                (('thanksBlock', 'thanks_block.html', {'post': post}),
                 ('postControls', 'post_controls.html', {'post': post})),
                additional={'status': 'SUCCESS'})

        return HttpResponseRedirect(post.get_url())
