# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestBlogPostScheduledPublication(TransactionCase):
    def setUp(self):
        super().setUp()
        # Create a blog
        self.blog = self.env["blog.blog"].create({"name": "Test Blog"})
        # Create a user with blog manager rights
        group_blog_manager = self.env.ref("website.group_website_designer")
        self.user_blogmanager = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Blog Manager",
                    "login": "blog_manager",
                    "email": "blog.manager@example.com",
                    "groups_id": [(6, 0, [group_blog_manager.id])],
                }
            )
        )

    def test_scheduled_publication_future_date(self):
        """Test that a post with future scheduled date is not published immediately."""
        future_date = fields.Datetime.now() + timedelta(days=1)
        post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "Scheduled Post",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": future_date,
                    "website_published": True,  # Try to publish immediately
                }
            )
        )
        # Post should not be published because of future scheduled date
        self.assertFalse(
            post.website_published,
            "Post with future scheduled date should not be published immediately",
        )
        self.assertEqual(
            post.scheduled_publication_date,
            future_date,
            "Scheduled date should be preserved",
        )

    def test_scheduled_publication_past_date(self):
        """Test that a post with past scheduled date is published immediately."""
        past_date = fields.Datetime.now() - timedelta(days=1)
        post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "Past Scheduled Post",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": past_date,
                    "website_published": True,
                }
            )
        )
        # Post should be published immediately and scheduled date cleared
        self.assertTrue(
            post.website_published,
            "Post with past scheduled date should be published immediately",
        )
        self.assertFalse(
            post.scheduled_publication_date,
            "Past scheduled date should be cleared after publication",
        )

    def test_scheduled_publication_no_date(self):
        """Test that a post without scheduled date is published immediately."""
        post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "Immediate Post",
                    "blog_id": self.blog.id,
                    "website_published": True,
                }
            )
        )
        # Post should be published immediately
        self.assertTrue(
            post.website_published,
            "Post without scheduled date should be published immediately",
        )
        self.assertFalse(
            post.scheduled_publication_date,
            "Post without scheduled date should have no scheduled date",
        )

    def test_scheduled_publication_set_future_date_on_published_post(self):
        """Test that setting a future date on a published post unpublishes it."""
        post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "Published Post",
                    "blog_id": self.blog.id,
                    "website_published": True,
                }
            )
        )
        self.assertTrue(post.website_published, "Post should be published")

        # Set a future scheduled date
        future_date = fields.Datetime.now() + timedelta(days=1)
        post.with_context(mail_create_nolog=True).write(
            {"scheduled_publication_date": future_date}
        )

        # Post should be unpublished
        self.assertFalse(
            post.website_published,
            "Post should be unpublished when future scheduled date is set",
        )
        self.assertEqual(
            post.scheduled_publication_date,
            future_date,
            "Scheduled date should be set",
        )

    def test_scheduled_publication_clear_future_date(self):
        """Test that clearing a future scheduled date allows immediate publication."""
        future_date = fields.Datetime.now() + timedelta(days=1)
        post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "Scheduled Post",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": future_date,
                }
            )
        )
        self.assertFalse(post.website_published, "Post should not be published")

        # Clear scheduled date and publish
        post.with_context(mail_create_nolog=True).write(
            {"scheduled_publication_date": False, "website_published": True}
        )

        # Post should be published
        self.assertTrue(
            post.website_published,
            "Post should be published when scheduled date is cleared",
        )
        self.assertFalse(
            post.scheduled_publication_date,
            "Scheduled date should be cleared",
        )

    def test_cron_publish_scheduled_posts(self):
        """Test that cron job publishes scheduled posts when date arrives."""
        # Create posts with past scheduled dates
        past_date = fields.Datetime.now() - timedelta(hours=1)
        scheduled_post1 = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .create(
                {
                    "name": "Scheduled Post 1",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": past_date,
                    "website_published": False,
                }
            )
        )
        scheduled_post2 = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .create(
                {
                    "name": "Scheduled Post 2",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": past_date,
                    "website_published": False,
                }
            )
        )

        # Create a post with future scheduled date (should not be published)
        future_date = fields.Datetime.now() + timedelta(days=1)
        future_post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .create(
                {
                    "name": "Future Post",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": future_date,
                    "website_published": False,
                }
            )
        )

        # Run the cron job
        self.env["blog.post"]._publish_scheduled_posts()

        # Past scheduled posts should be published
        self.assertTrue(
            scheduled_post1.website_published,
            "Past scheduled post should be published by cron",
        )
        self.assertFalse(
            scheduled_post1.scheduled_publication_date,
            "Scheduled date should be cleared after publication",
        )

        self.assertTrue(
            scheduled_post2.website_published,
            "Past scheduled post should be published by cron",
        )
        self.assertFalse(
            scheduled_post2.scheduled_publication_date,
            "Scheduled date should be cleared after publication",
        )

        # Future post should not be published
        self.assertFalse(
            future_post.website_published,
            "Future scheduled post should not be published by cron",
        )
        self.assertEqual(
            future_post.scheduled_publication_date,
            future_date,
            "Future scheduled date should be preserved",
        )

    def test_cron_skip_inactive_posts(self):
        """Test that cron job skips inactive posts."""
        past_date = fields.Datetime.now() - timedelta(hours=1)
        inactive_post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .create(
                {
                    "name": "Inactive Post",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": past_date,
                    "website_published": False,
                    "active": False,
                }
            )
        )

        # Run the cron job
        self.env["blog.post"]._publish_scheduled_posts()

        # Inactive post should not be published
        self.assertFalse(
            inactive_post.website_published,
            "Inactive post should not be published by cron",
        )

    def test_cron_skip_already_published_posts(self):
        """Test that cron job skips already published posts."""
        past_date = fields.Datetime.now() - timedelta(hours=1)
        published_post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .create(
                {
                    "name": "Already Published Post",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": past_date,
                    "website_published": True,
                }
            )
        )

        # Run the cron job
        self.env["blog.post"]._publish_scheduled_posts()

        # Post should remain published
        self.assertTrue(
            published_post.website_published,
            "Already published post should remain published",
        )

    def test_scheduled_publication_string_to_datetime_conversion(self):
        """Test that string dates are properly converted to datetime."""
        future_date = fields.Datetime.now() + timedelta(days=1)
        future_date_str = fields.Datetime.to_string(future_date)

        post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "String Date Post",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": future_date_str,
                    "website_published": True,
                }
            )
        )

        # Post should not be published because of future scheduled date
        self.assertFalse(
            post.website_published,
            "Post with future scheduled date (string) should not be published",
        )
        # Scheduled date should be stored and not False
        self.assertTrue(
            post.scheduled_publication_date,
            "Scheduled date should be stored",
        )
        # Verify the date is correct (allowing for small time differences)
        stored_date = fields.Datetime.from_string(
            fields.Datetime.to_string(post.scheduled_publication_date)
        )
        expected_date = fields.Datetime.from_string(future_date_str)
        self.assertEqual(
            stored_date,
            expected_date,
            "Scheduled date should match the original date",
        )

    def test_write_without_scheduled_date_or_publication(self):
        """Test that write without scheduled date or publication uses standard write."""
        post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "Test Post",
                    "blog_id": self.blog.id,
                }
            )
        )
        # Write without scheduled date or publication should work normally
        post.write({"name": "Updated Post Name"})
        self.assertEqual(post.name, "Updated Post Name")

    def test_write_set_past_date_on_unpublished_post(self):
        """Test that setting a past date on unpublished post clears the date."""
        future_date = fields.Datetime.now() + timedelta(days=1)
        post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "Scheduled Post",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": future_date,
                    "website_published": False,
                }
            )
        )
        # Set a past date
        past_date = fields.Datetime.now() - timedelta(hours=1)
        post.write({"scheduled_publication_date": past_date})

        # Past date should be cleared
        self.assertFalse(
            post.scheduled_publication_date,
            "Past scheduled date should be cleared when set on unpublished post",
        )

    def test_write_publish_with_existing_past_scheduled_date(self):
        """Test publishing a post that has an existing past scheduled date."""
        past_date = fields.Datetime.now() - timedelta(hours=1)
        post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "Post with Past Date",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": past_date,
                    "website_published": False,
                }
            )
        )
        # Publish the post (scheduled date exists but not in vals)
        post.with_context(mail_create_nolog=True).write({"website_published": True})

        # Post should be published and scheduled date cleared
        self.assertTrue(
            post.website_published,
            "Post should be published when publishing with existing past scheduled date",
        )
        self.assertFalse(
            post.scheduled_publication_date,
            "Past scheduled date should be cleared after publication",
        )

    def test_write_multiple_records_different_scheduled_dates(self):
        """Test write with multiple records having different scheduled dates."""
        future_date = fields.Datetime.now() + timedelta(days=1)
        past_date = fields.Datetime.now() - timedelta(hours=1)

        post1 = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "Post 1",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": future_date,
                    "website_published": False,
                }
            )
        )
        post2 = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "Post 2",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": past_date,
                    "website_published": False,
                }
            )
        )

        # Try to publish both posts
        posts = post1 | post2
        posts.with_context(mail_create_nolog=True).write({"website_published": True})

        # Post1 should not be published (future date)
        self.assertFalse(
            post1.website_published,
            "Post with future scheduled date should not be published",
        )
        # Post2 should be published (past date)
        self.assertTrue(
            post2.website_published,
            "Post with past scheduled date should be published",
        )
        self.assertFalse(
            post2.scheduled_publication_date,
            "Past scheduled date should be cleared after publication",
        )

    def test_create_with_past_date_not_publishing(self):
        """Test creating a post with past date but not publishing."""
        past_date = fields.Datetime.now() - timedelta(hours=1)
        post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .create(
                {
                    "name": "Post with Past Date",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": past_date,
                    "website_published": False,
                }
            )
        )
        # Past date should be kept for cron to handle
        self.assertFalse(post.website_published, "Post should not be published")
        self.assertEqual(
            post.scheduled_publication_date,
            past_date,
            "Past scheduled date should be preserved when not publishing",
        )

    def test_create_with_future_date_not_publishing(self):
        """Test creating a post with future date but not publishing."""
        future_date = fields.Datetime.now() + timedelta(days=1)
        post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .create(
                {
                    "name": "Post with Future Date",
                    "blog_id": self.blog.id,
                    "scheduled_publication_date": future_date,
                    "website_published": False,
                }
            )
        )
        # Future date should be kept
        self.assertFalse(post.website_published, "Post should not be published")
        self.assertEqual(
            post.scheduled_publication_date,
            future_date,
            "Future scheduled date should be preserved",
        )

    def test_write_set_past_date_on_published_post(self):
        """Test that setting a past date on published post publishes immediately."""
        post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "Published Post",
                    "blog_id": self.blog.id,
                    "website_published": True,
                }
            )
        )
        # Set a past scheduled date
        past_date = fields.Datetime.now() - timedelta(hours=1)
        post.with_context(mail_create_nolog=True).write(
            {"scheduled_publication_date": past_date}
        )

        # Post should remain published and scheduled date cleared
        self.assertTrue(
            post.website_published,
            "Post should remain published when past date is set",
        )
        self.assertFalse(
            post.scheduled_publication_date,
            "Past scheduled date should be cleared",
        )

    def test_cron_empty_result(self):
        """Test that cron handles empty result gracefully."""
        # Run cron when there are no scheduled posts
        result = self.env["blog.post"]._publish_scheduled_posts()
        self.assertTrue(result, "Cron should return True even with no posts")

    def test_check_for_publication_with_mail_create_nolog(self):
        """Test that _check_for_publication respects mail_create_nolog context."""
        post = (
            self.env["blog.post"]
            .with_user(self.user_blogmanager)
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "Test Post",
                    "blog_id": self.blog.id,
                    "website_published": True,
                }
            )
        )
        # _check_for_publication should return False when mail_create_nolog is set
        result = post._check_for_publication({"is_published": True})
        self.assertFalse(result, "Should return False when mail_create_nolog is set")
