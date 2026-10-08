.DEFAULT_GOAL := all

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PYTHON ?= python3
TARGET ?= $(CURDIR)

.PHONY: all
all:
	@$(PYTHON) "$(ROOT)/scripts/bootstrap.py" --target "$(TARGET)"
