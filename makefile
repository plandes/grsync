## makefile automates the build and deployment for python projects

PROJ_TYPE=	python
WHINE=		1
CONFIG=		test-resources/grsync.yml

# make build dependencies
_ :=	$(shell [ ! -d .git ] && git init ; [ ! -d zenbuild ] && \
	  git submodule add https://github.com/plandes/zenbuild && make gitinit )

include ./zenbuild/main.mk

.PHONY:		discover
discover:
		make PYTHON_BIN_ARGS='info -c $(CONFIG) -w $(WHINE)' run

.PHONY:		freeze
freeze:
		make PYTHON_BIN_ARGS='freeze -c $(CONFIG) -w $(WHINE)' run

.PHONY:		thaw
thaw:
		rm -rf $(MTARG)/t
		make PYTHON_BIN_ARGS='thaw -d $(MTARG) -t $(MTARG)/t -w $(WHINE)' run

.PHONY:		appinfo
appinfo:
		rm -rf $(MTARG)/t
		make PYTHON_BIN_ARGS='info -c $(CONFIG)' run

.PHONY:		help
help:
		rm -rf $(MTARG)/t
		make PYTHON_BIN_ARGS='--help' run

.PHONY:		rethaw
rethaw:		clean freeze thaw

.PHONY:		delete
delete:
		make PYTHON_BIN_ARGS='delete --dryrun -t $(MTARG)/t -c $(CONFIG) -w $(WHINE)' run
