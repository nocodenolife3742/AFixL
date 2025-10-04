CC := gcc
CFLAGS := -Wall -Wextra -std=c11 -O0 -g -fsanitize=address,undefined
SOURCES := main.c
TARGET := example

all: $(TARGET)

$(TARGET): $(SOURCES)
	$(CC) $(CFLAGS) $^ -o $@

clean:
	rm -f $(TARGET)

.PHONY: all clean