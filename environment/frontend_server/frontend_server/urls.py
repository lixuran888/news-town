"""frontend_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import include, url
from django.urls import path
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

from translator import views as translator_views

urlpatterns = [
    url(r'^$', translator_views.landing, name='landing'),
    url(r'^start_time_setup/$', translator_views.start_time_setup, name='start_time_setup'),
    url(r'^check_start_time_configured/$', translator_views.check_start_time_configured, name='check_start_time_configured'),
    url(r'^simulator_home$', translator_views.home, name='home'),
    url(r'^demo/(?P<sim_code>[\w-]+)/(?P<step>[\w-]+)/(?P<play_speed>[\w-]+)/$', translator_views.demo, name='demo'),
    url(r'^replay/(?P<sim_code>[\w-]+)/(?P<step>[\w-]+)/$', translator_views.replay, name='replay'),
    url(r'^replay_persona_state/(?P<sim_code>[\w-]+)/(?P<step>[\w-]+)/(?P<persona_name>[\w-]+)/$', translator_views.replay_persona_state, name='replay_persona_state'),
    url(r'^process_environment/$', translator_views.process_environment, name='process_environment'),
    url(r'^update_environment/$', translator_views.update_environment, name='update_environment'),
    url(r'^path_tester/$', translator_views.path_tester, name='path_tester'),
    url(r'^path_tester_update/$', translator_views.path_tester_update, name='path_tester_update'),
    url(r'^check_expert_meeting/$', translator_views.expert_meeting_trigger, name='check_expert_meeting'),
    url(r'^dismiss_expert_meeting/$', translator_views.dismiss_expert_meeting, name='dismiss_expert_meeting'),
    # 线上舆论广场
    url(r'^online_forum/$', translator_views.online_forum, name='online_forum'),
    url(r'^get_online_posts/$', translator_views.get_online_posts, name='get_online_posts'),
    url(r'^post_online_opinion/$', translator_views.post_online_opinion, name='post_online_opinion'),
    # 舆论与情感时间序列
    url(r'^sentiment_timeline/$', translator_views.sentiment_timeline, name='sentiment_timeline'),
    # 舆论统计图表（数量+情感）
    url(r'^opinion_statistics_chart/$', translator_views.opinion_statistics_chart, name='opinion_statistics_chart'),
    path('admin/', admin.site.urls),
]
