# Makefile to generate sounds.h

sounds.h: sounds/*
	./convert-sounds.sh sounds/*
