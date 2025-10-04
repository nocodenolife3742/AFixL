#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void crash_me(const char *input) {
    if (strncmp(input, "c", 1) == 0) {
        int *p = NULL;
        *p = 42;
    }
}

int main(int argc, char *argv[]) {
    // read input from argv[1]
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <input>\n", argv[0]);
        return 1;
    }

    // read file content
    FILE *file = fopen(argv[1], "r");
    if (!file) {
        perror("fopen");
        return 1;
    }

    char buffer[256];
    size_t len = fread(buffer, 1, sizeof(buffer) - 1, file);
    buffer[len] = '\0';
    fclose(file);
    crash_me(buffer);

    return 0;
}