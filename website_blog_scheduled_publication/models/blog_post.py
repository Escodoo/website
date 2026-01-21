# Copyright 2026 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class BlogPost(models.Model):
    _inherit = "blog.post"

    scheduled_publication_date = fields.Datetime(
        help="If set, the blog post will be automatically published on this date and time. "
        "Leave empty to publish immediately when marked as published.",
    )

    @api.model
    def _publish_scheduled_posts(self):
        """Cron job method to publish scheduled blog posts."""
        now = fields.Datetime.now()
        scheduled_posts = self.search(
            [
                ("scheduled_publication_date", "<=", now),
                ("scheduled_publication_date", "!=", False),
                ("website_published", "=", False),
                ("active", "=", True),
            ]
        )
        if scheduled_posts:
            scheduled_posts.with_context(mail_create_nolog=True).write(
                {"website_published": True}
            )
            # Clear scheduled date after publishing
            scheduled_posts.write({"scheduled_publication_date": False})
        return True

    def _check_for_publication(self, vals):
        """Override to respect mail_create_nolog context."""
        if self.env.context.get("mail_create_nolog"):
            # Skip publication notification if mail_create_nolog is set
            return False
        return super()._check_for_publication(vals)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle scheduled publication during creation."""
        now = fields.Datetime.now()

        # Helper function to convert string to datetime if needed
        def to_datetime(value):
            if not value:
                return False
            if isinstance(value, str):
                return fields.Datetime.from_string(value)
            return value

        # Process each vals dict to handle scheduled dates
        processed_vals_list = []
        for vals in vals_list:
            processed_vals = vals.copy()

            # Check if there's a scheduled publication date
            if "scheduled_publication_date" in processed_vals:
                scheduled_date = to_datetime(
                    processed_vals.get("scheduled_publication_date")
                )
                # If setting a future scheduled date and trying to publish
                if scheduled_date and scheduled_date > now:
                    if processed_vals.get("website_published"):
                        processed_vals["website_published"] = False
                # If past date and trying to publish, allow immediate publication and clear date
                elif scheduled_date and scheduled_date <= now:
                    if processed_vals.get("website_published"):
                        processed_vals["scheduled_publication_date"] = False
                    # If not publishing, keep the past date (for cron to handle)

            # Check if trying to publish without scheduled date
            elif processed_vals.get("website_published"):
                # Allow immediate publication if no scheduled date
                pass

            processed_vals_list.append(processed_vals)

        return super().create(processed_vals_list)

    def write(self, vals):
        """Override write to handle scheduled publication logic."""
        now = fields.Datetime.now()

        # Helper function to convert string to datetime if needed
        def to_datetime(value):
            if not value:
                return False
            if isinstance(value, str):
                return fields.Datetime.from_string(value)
            return value

        # Only process if dealing with scheduled dates or publication
        if "scheduled_publication_date" in vals or "website_published" in vals:
            # Process each record to handle individual scheduled dates
            records_to_write = []
            for record in self:
                record_vals = vals.copy()

                # Get the scheduled date that will be effective after this write
                if "scheduled_publication_date" in record_vals:
                    scheduled_date = to_datetime(
                        record_vals.get("scheduled_publication_date")
                    )
                else:
                    scheduled_date = to_datetime(record.scheduled_publication_date)

                # Handle scheduled publication date changes
                if "scheduled_publication_date" in record_vals:
                    new_scheduled_date_raw = record_vals.get(
                        "scheduled_publication_date"
                    )
                    new_scheduled_date = to_datetime(new_scheduled_date_raw)
                    # If setting a future scheduled date
                    if new_scheduled_date and new_scheduled_date > now:
                        # Unpublish if currently published or will be published
                        will_be_published = record_vals.get(
                            "website_published", record.website_published
                        )
                        if will_be_published:
                            record_vals["website_published"] = False
                        # Keep the original value format (string or datetime)
                        record_vals[
                            "scheduled_publication_date"
                        ] = new_scheduled_date_raw
                    # If clearing or setting to past, clear the field
                    elif new_scheduled_date and new_scheduled_date <= now:
                        record_vals["scheduled_publication_date"] = False

                # Handle publication request
                if "website_published" in record_vals and record_vals.get(
                    "website_published"
                ):
                    # If there's a future scheduled date, don't publish now
                    if scheduled_date and scheduled_date > now:
                        record_vals["website_published"] = False
                        # Ensure scheduled date is set
                        if "scheduled_publication_date" not in record_vals:
                            record_vals["scheduled_publication_date"] = scheduled_date
                    # If scheduled date is past or empty, allow immediate publication
                    elif scheduled_date and scheduled_date <= now:
                        # Clear past scheduled date
                        record_vals["scheduled_publication_date"] = False

                records_to_write.append((record, record_vals))

            # Write to all records
            for record, record_vals in records_to_write:
                # Preserve context (especially mail_create_nolog) when writing
                # Use super() to avoid recursion
                super(BlogPost, record.with_context(**self.env.context)).write(
                    record_vals
                )
            return self
        else:
            # No scheduled date logic needed, use standard write
            return super().write(vals)
