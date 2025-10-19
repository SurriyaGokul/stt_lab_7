#include <stdio.h>
#include <string.h>

#define MAX_STUDENTS 50
#define MAX_NAME 32

typedef struct {
    char name[MAX_NAME];
    int m1, m2, m3;
    float avg;
    char grade;
} Student;

void compute_avg_and_grade(Student *s) {
    s->avg = (s->m1 + s->m2 + s->m3) / 3.0f;
    if (s->avg >= 90.0f) {
        s->grade = 'A';
    } else if (s->avg >= 80.0f) {
        s->grade = 'B';
    } else if (s->avg >= 70.0f) {
        s->grade = 'C';
    } else if (s->avg >= 60.0f) {
        s->grade = 'D';
    } else {
        s->grade = 'F';
    }
}

void curve_class(Student arr[], int n, float target_avg) {
    // Increase all averages toward target using a simple curve (max 5 points per subject)
    // Demonstrates nested if inside loops + multiple assignments
    int i;
    for (i = 0; i < n; i++) {
        float delta = target_avg - arr[i].avg;
        if (delta > 0.0f) {
            int bump = (delta > 10.0f) ? 10 : (int)(delta + 0.5f);
            // distribute bump across subjects
            int add1 = bump / 3;
            int add2 = bump / 3;
            int add3 = bump - add1 - add2;
            arr[i].m1 = arr[i].m1 + add1;
            arr[i].m2 = arr[i].m2 + add2;
            arr[i].m3 = arr[i].m3 + add3;

            if (arr[i].m1 > 100) arr[i].m1 = 100;
            if (arr[i].m2 > 100) arr[i].m2 = 100;
            if (arr[i].m3 > 100) arr[i].m3 = 100;
            compute_avg_and_grade(&arr[i]);
        }
    }
}

void sort_by_avg_desc(Student arr[], int n) {
    // Bubble sort using while + for
    int swapped = 1;
    while (swapped) {
        swapped = 0;
        for (int i = 0; i < n - 1; i++) {
            if (arr[i].avg < arr[i+1].avg) {
                Student tmp = arr[i];
                arr[i] = arr[i+1];
                arr[i+1] = tmp;
                swapped = 1;
            }
        }
    }
}

int find_student(Student arr[], int n, const char *name) {
    for (int i = 0; i < n; i++) {
        if (strcmp(arr[i].name, name) == 0) return i;
    }
    return -1;
}

int main(void) {
    Student cls[MAX_STUDENTS];
    int n;
    printf("Enter number of students (<= %d): ", MAX_STUDENTS);
    if (scanf("%d", &n) != 1 || n <= 0 || n > MAX_STUDENTS) {
        printf("Invalid n\n");
        return 0;
    }

    for (int i = 0; i < n; i++) {
        printf("Name and three marks for student %d:\n", i+1);
        if (scanf("%31s %d %d %d", cls[i].name, &cls[i].m1, &cls[i].m2, &cls[i].m3) != 4) {
            printf("Bad input\n");
            return 0;
        }
        if (cls[i].m1 < 0) cls[i].m1 = 0;
        if (cls[i].m2 < 0) cls[i].m2 = 0;
        if (cls[i].m3 < 0) cls[i].m3 = 0;
        if (cls[i].m1 > 100) cls[i].m1 = 100;
        if (cls[i].m2 > 100) cls[i].m2 = 100;
        if (cls[i].m3 > 100) cls[i].m3 = 100;
        compute_avg_and_grade(&cls[i]);
    }

    // Optional curve
    float desired;
    printf("Enter desired class average (0-100): ");
    if (scanf("%f", &desired) == 1 && desired > 0.0f && desired <= 100.0f) {
        curve_class(cls, n, desired);
    }

    sort_by_avg_desc(cls, n);

    printf("\n=== Class Summary (sorted by avg) ===\n");
    float sum = 0.0f; int countA = 0, countF = 0;
    for (int i = 0; i < n; i++) {
        sum += cls[i].avg;
        if (cls[i].grade == 'A') countA++;
        if (cls[i].grade == 'F') countF++;
        printf("%-12s  m=(%3d,%3d,%3d)  avg=%6.2f  grade=%c\n",
            cls[i].name, cls[i].m1, cls[i].m2, cls[i].m3, cls[i].avg, cls[i].grade);
    }
    float class_avg = (n > 0) ? (sum / n) : 0.0f;
    printf("Class average: %.2f | A's: %d | F's: %d\n", class_avg, countA, countF);

    // Query loop using while and if/else
    char qname[MAX_NAME];
    printf("\nQuery by name (type END to stop):\n");
    while (1) {
        if (scanf("%31s", qname) != 1) break;
        if (strcmp(qname, "END") == 0) break;
        int idx = find_student(cls, n, qname);
        if (idx >= 0) {
            printf("Found: %s avg=%.2f grade=%c\n", cls[idx].name, cls[idx].avg, cls[idx].grade);
        } else {
            printf("Student not found.\n");
        }
    }
    return 0;
}
