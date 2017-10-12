#!/bin/bash
cd $SCIFLO_DIR
mysqladmin -S $SCIFLO_DIR/log/mysqld.sock -u root shutdown -p
