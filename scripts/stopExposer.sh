#!/bin/bash
ps -C python | awk '{print $1}' | xargs -i -t grep exposer /proc/{}/cmdline 2>/dev/null | grep matches | awk 'BEGIN{FS="/"}{print $3}' | xargs kill -9 > /dev/null 2>&1
