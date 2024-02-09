SRC = src
INCLUDE = $(SRC)/include
BUILD = build

CC = gcc
CFLAGS = -Wall -Wextra -O2 -I $(INCLUDE)

C_FILES := \
	malloc_freelist.c \
	main.c \

O_FILES := $(patsubst %.c, $(BUILD)/%.o, $(C_FILES))

MAIN := $(BUILD)/main

.PHONY: run
run: $(MAIN)
	$(MAIN)

$(BUILD)/%.o: $(SRC)/%.c
	$(CC) -c $(CFLAGS) -o $@ $<

$(MAIN): $(O_FILES)
	$(CC) $(LDFLAGS)  $(O_FILES) -o $(MAIN)


.PHONY: clean
clean:
	rm -rf build/*
