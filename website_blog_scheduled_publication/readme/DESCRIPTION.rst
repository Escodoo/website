This module allows you to schedule blog posts for automatic publication at a specific date and time.

Features
--------

* Add a "Scheduled Publication Date" field to blog posts
* Automatically publish posts when the scheduled date arrives
* Prevent immediate publication if a future date is scheduled
* Automatic cron job runs every hour to check and publish scheduled posts

Usage
-----

When creating or editing a blog post, you can set the "Scheduled Publication Date" field. If you set a future date, the post will not be published immediately even if you mark it as published. The post will be automatically published when the scheduled date and time arrives.

The cron job runs every hour to check for posts that should be published.
