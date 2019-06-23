## makefile automates the build and deployment for python projects

PROJ_TYPE=	python
#ARGS=		-w 2
#ARGS=		-p osx
#CONFIG=		test-resources/small-test.yml
CONFIG=		$(GRSYNCRC)

ADD_CLEAN=	dist

include zenbuild/main.mk

.PHONY:		discover
discover:
		make PYTHON_BIN_ARGS='info -c $(CONFIG) $(ARGS)' run

.PHONY:		repos
repos:
		make PYTHON_BIN_ARGS='repos -c $(CONFIG) $(ARGS) ' run

.PHONY:		repoinfo
repoinfo:
		make PYTHON_BIN_ARGS='repoinfo -c $(CONFIG) $(ARGS) -n home-dir' run

.PHONY:		freeze
freeze:
		mkdir -p $(MTARG)
		make PYTHON_BIN_ARGS='freeze -c $(CONFIG) -d $(MTARG)/dist $(ARGS)' run

.PHONY:		thaw
thaw:
		rm -rf $(MTARG)/t
		make PYTHON_BIN_ARGS='thaw -d $(MTARG) -t $(MTARG)/t $(ARGS)' run

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
		make PYTHON_BIN_ARGS='delete --dryrun -t $(MTARG)/t -c $(CONFIG) $(ARGS)' run

.PHONY:		testfreezethaw
testfreezethaw:
		make PY_SRC_TEST_PKGS=test_freeze.TestFreezeThaw.test_freeze test
#		make PY_SRC_TEST_PKGS=test_freeze.TestFreezeThaw.test_thaw test

.PHONY:		testmove
testmove:
		make PY_SRC_TEST_PKGS=test_freeze.TestFreezeThaw.test_move test
