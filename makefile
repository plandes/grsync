## makefile automates the build and deployment for python projects


## Build
#
PROJ_TYPE=		python
PROJ_MODULES =		python/doc python/package python/deploy python/envdist


## Project
#
CONFIG_FILE ?=		test-resources/midsize-test.yml


## Includes
#
include ./zenbuild/main.mk


## Functions
#
define run
	$(MAKE) $(PY_MAKE_ARGS) pyharn ARG="--config $(CONFIG_FILE) $(1)"
endef


## Targets
#
# pretty print discovery information
.PHONY:		discover
discover:
		@$(call run,info)

# output all repository top level info
.PHONY:		repos
repos:
		@$(call run,repos)
