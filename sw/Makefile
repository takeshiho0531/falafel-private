SRC = src
INCLUDE = $(SRC)/include
BUILD = build

CC = gcc
# CFLAGS = -g -Wall -Wextra -O2 -I $(INCLUDE)
CFLAGS = -g -Wall -Wextra -g -I $(INCLUDE)

C_FILES := \
	malloc_freelist.c \
	main.c \

O_FILES := $(patsubst %.c, $(BUILD)/%.o, $(C_FILES))

MAIN := $(BUILD)/main

.PHONY: run
run: $(MAIN)
	$(MAIN)

.PHONY: debug
debug: $(MAIN)
	gdb $(MAIN)

$(BUILD)/%.o: $(SRC)/%.c
	$(CC) -c $(CFLAGS) -o $@ $<

$(MAIN): $(O_FILES)
	$(CC) $(LDFLAGS)  $(O_FILES) -o $(MAIN)



.PHONY: clean
clean:
	rm -rf build/*
