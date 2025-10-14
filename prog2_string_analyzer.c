
/*
  Program 2: String & Word Analyzer
  - Features: character classification, tokenization, palindrome checks,
    for + while loops, nested ifs, aggregations with assignments.
  - No switch/goto; standard C only.
*/
#include <stdio.h>
#include <string.h>
#include <ctype.h>

#define MAX_LINE 1024
#define MAX_WORDS 200
#define MAX_WORD 64

int is_vowel(char c) {
    char d = (char)tolower((unsigned char)c);
    return d=='a'||d=='e'||d=='i'||d=='o'||d=='u';
}

int is_pal(const char *s) {
    int i = 0, j = (int)strlen(s) - 1;
    while (i < j) {
        if (s[i] != s[j]) return 0;
        i++; j--;
    }
    return 1;
}

int main(void) {
    char line[MAX_LINE];
    char words[MAX_WORDS][MAX_WORD];
    int wcount = 0;

    printf("Enter a line (<= 1023 chars):\n");
    if (!fgets(line, sizeof(line), stdin)) {
        return 0;
    }

    // Tokenize by spaces and punctuation
    int i = 0;
    while (line[i] != '\0' && wcount < MAX_WORDS) {
        while (line[i] && !isalnum((unsigned char)line[i])) i++;
        if (!line[i]) break;
        int k = 0;
        while (line[i] && isalnum((unsigned char)line[i]) && k < MAX_WORD-1) {
            words[wcount][k++] = (char)tolower((unsigned char)line[i]);
            i++;
        }
        words[wcount][k] = '\0';
        if (k > 0) wcount++;
        while (line[i] && isalnum((unsigned char)line[i])) i++; // skip overlong token tail
    }

    int letters = 0, digits = 0, spaces = 0, vowels = 0, consonants = 0;
    for (i = 0; line[i]; i++) {
        unsigned char c = (unsigned char)line[i];
        if (isalpha(c)) {
            letters++;
            if (is_vowel(c)) vowels++;
            else consonants++;
        } else if (isdigit(c)) {
            digits++;
        } else if (isspace(c)) {
            spaces++;
        }
    }

    // Simple frequency count of the first 26 words (by first letter)
    int freq[26] = {0};
    for (i = 0; i < wcount; i++) {
        char c = words[i][0];
        if (c >= 'a' && c <= 'z') {
            freq[c - 'a'] = freq[c - 'a'] + 1; // explicit assignment
        }
    }

    // Palindrome count and longest word
    int pal_count = 0, max_len = 0, max_idx = -1;
    for (i = 0; i < wcount; i++) {
        if (is_pal(words[i])) pal_count++;
        int L = (int)strlen(words[i]);
        if (L > max_len) {
            max_len = L;
            max_idx = i;
        }
    }

    printf("Words: %d | Letters: %d | Digits: %d | Spaces: %d\n", wcount, letters, digits, spaces);
    printf("Vowels: %d | Consonants: %d | Palindromes: %d\n", vowels, consonants, pal_count);
    if (max_idx >= 0) {
        printf("Longest word: %s (%d)\n", words[max_idx], max_len);
    }

    // Show first-letter histogram for letters seen
    printf("\nHistogram (first letter of word):\n");
    for (i = 0; i < 26; i++) {
        if (freq[i] > 0) {
            printf("%c: %d\n", 'a' + i, freq[i]);
        }
    }

    // Filter words by min length (demonstrates while + if)
    int minL;
    printf("\nEnter a minimum length to list words: ");
    if (scanf("%d", &minL) == 1 && minL > 0) {
        int printed = 0;
        for (i = 0; i < wcount; i++) {
            if ((int)strlen(words[i]) >= minL) {
                printf("%s\n", words[i]);
                printed++;
            }
        }
        if (printed == 0) {
            printf("No words with length >= %d\n", minL);
        }
    }
    return 0;
}
