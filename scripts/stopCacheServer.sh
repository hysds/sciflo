#!/bin/bash
\ps x | grep [t]wistd | awk '{print $1}' | xargs kill -15 2>/dev/null
