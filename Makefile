all: start

up:start
start:
	@./bin/start.sh
down: stop
stop:
	@./bin/stop.sh

distclean:
	find ./ -name '*.pyc' | xargs rm -f
	rm -rf tests/__pycache__

.PHONY: test vagrant-up vagrant-halt frontend-lint frontend-start shell

test:
	python -mpytest tests/test_*.py

install:
	pip install -r requirements.pip

vagrant-up:
	@cd vagrant && vagrant up

vagrant-halt:
	@cd vagrant && vagrant halt

lint:
	@pyflakes app
	@pychecker -Q --only app

frontend-start: #frontend-lint
	@mkdir -p run
	@python -mapp --logging logging.conf 

shell:
	@cd vagrant && vagrant ssh
