# -*- coding: utf-8 -*-
import os
import subprocess
import logging
from shutil import copytree, rmtree
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class AutoRebuild(models.Model):
    _name = 'auto.rebuild'
    _description = 'Auto Rebuild Database and Filestore'

    last_rebuild_date = fields.Datetime(string='Last Rebuild Date', readonly=True)

    def run_command(self, command):
        """Run a shell command."""
        result = subprocess.run(command, shell=True, capture_output=True)
        if result.returncode != 0:
            raise Exception(f"Command failed: {command}\n{result.stderr.decode()}")
        return result.stdout.decode()

    def dump_prod_db(self, settings):
        """Dump the production database."""
        command = f"PGPASSWORD={settings.prod_db_password} pg_dump -U {settings.prod_db_user} -h {settings.prod_host} {settings.prod_db_name} > /tmp/prod_db_dump.sql"
        self.run_command(command)
        _logger.info("Auto rebuild: Production database dumped successfully")

    def copy_to_uat(self, settings):
        """Copy the database dump and filestore to UAT server."""
        scp_db_command = f"scp /tmp/prod_db_dump.sql root@{settings.uat_host}:/tmp/prod_db_dump.sql"
        scp_filestore_command = f"scp -r {settings.prod_filestore} root@{settings.uat_host}:{settings.uat_filestore}"
        self.run_command(scp_db_command)
        self.run_command(scp_filestore_command)
        _logger.info("AutoRebuild: Database dump and filestore copied to UAT server successfully")

    def restore_uat_db(self, settings):
        """Restore the database on the UAT server."""

        drop_command = f"PGPASSWORD={settings.uat_db_password} psql -U {settings.uat_db_user} -h {settings.prod_host} -c 'DROP DATABASE IF EXISTS {settings.uat_db_name}'"
        create_command = f"PGPASSWORD={settings.uat_db_password} psql -U {settings.uat_db_user} -h {settings.prod_host} -c 'CREATE DATABASE {settings.uat_db_name}'"
        restore_command = f"PGPASSWORD={settings.uat_db_password} psql -U {settings.uat_db_user} -h {settings.prod_host} {settings.uat_db_name} < /tmp/prod_db_dump.sql"
        self.run_command(drop_command)
        self.run_command(create_command)
        self.run_command(restore_command)
        _logger.info("AutoRebuild: UAT database restored successfully.")

    def update_uat_filestore(self, settings):
        """Update the filestore on the UAT server."""
        if os.path.exists(settings.uat_filestore):
            rmtree(settings.uat_filestore)
        copytree(settings.prod_filestore, settings.uat_filestore)
        _logger.info("AutoRebuild: UAT filestore updated successfully")

    def rebuild_database_and_filestore(self):
        """Main function to automate the rebuild process."""
        settings = self.env['auto.rebuild.settings'].search([], limit=1)
        if not settings:
            raise Exception("Auto Rebuild settings not found!")

        self.dump_prod_db(settings)
        self.copy_to_uat(settings)
        self.restore_uat_db(settings)
        self.update_uat_filestore(settings)
        _logger.info("AutoRebuild: Database and filestore rebuild process completed successfully.")
        self.last_rebuild_date = fields.Datetime.now()

    def button_rebuild(self):
        """Button action to initiate the rebuild process."""
        self.rebuild_database_and_filestore()
