from django.test import TestCase
import datetime
from django.contrib.auth.models import AnonymousUser, User

from .models import Citation, Thread, Post
from .views import order_post_list

class postScoreTests(TestCase):

    def setUp(self):
        # create a citation
        citation = Citation(title="my citation",author='michael',journal='science',
                            volume='1',number='2',pages='3-4',date='2015',
                            fullSource='science(1),3-4,2015',keywords='worms',
                            abstract='worms are cool',doi='102:324522',
                            fullAuthorNames='Michael Chiang', pubmedID='12345')
        citation.save()

        # create a thread linked to citation
        thread = Thread(owner=citation, description="discussion")
        thread.save()

        # create users
        try:
            user1 = User.objects.create_user(username='user1', email='user1@gmail.com', password='password1')
        except:
            user1 = User.objects.get(username='user1')
        try:
            user2 = User.objects.create_user(username='user2', email='user2@gmail.com', password='password2')
        except:
            user2 = User.objects.get(username='user2')

        # user1 creates master post
        post0 = Post(time_created=datetime.datetime.now(),creator=user1,thread=thread,
                    isReplyToPost=False,text="master",node_depth=0)
        post0.save()

        # user1 creates post
        post1 = Post(time_created=datetime.datetime.now(),creator=user1,thread=thread,
                    isReplyToPost=True,mother=post0,text="user1's first post",node_depth=1)
        post1.save()
        # user2 creates post
        post3 = Post(time_created=datetime.datetime.now(),creator=user2,thread=thread,
                    isReplyToPost=True,mother=post0,text="user2's first post",node_depth=1)
        post3.save()
        # user2 replies to post
        post2 = Post(time_created=datetime.datetime.now(),creator=user2,thread=thread,
                     isReplyToPost=True,mother=post1,text="user2's first reply to user 1",node_depth=2)
        post2.save()
        # user2 upvotes his own reply and downvotes user1's post
        post2.upvoters.add(user2)
        post1.downvoters.add(user1)
        post1.save()
        post2.save()

    # Tests whether Post.score is working properly
    def test_raw_scores(self):
        post1 = Post.objects.get(text="user1's first post")
        post2 = Post.objects.get(text="user2's first reply to user 1")
        self.assertEqual(post1.score(),-1)
        self.assertEqual(post2.score(),1)

    # Tests whether aggregate scoring function is working correctly
    def test_aggregate_scores(self):
        post1 = Post.objects.get(text="user1's first post")
        post2 = Post.objects.get(text="user2's first reply to user 1")
        thread = Thread.objects.get(description="discussion")

        tree = Post.objects.filter(thread=thread)
        ordered_tree,tree = order_post_list(tree)

        idx_post1 = tree.filter(text__lt = "user1's first post").count()
        idx_post2 = tree.filter(text__lt = "user2's first reply").count()
        post1 = tree[idx_post1]
        post2 = tree[idx_post2]
        self.assertEqual(post1.aggregate_score_tmp,1)
        self.assertEqual(post2.aggregate_score_tmp,1)
        self.assertEqual(ordered_tree[0].text,'master')
        self.assertEqual(ordered_tree[1].text,"user1's first post")
        self.assertEqual(ordered_tree[2].text,"user2's first reply to user 1")
        self.assertEqual(ordered_tree[3].text,"user2's first post")
