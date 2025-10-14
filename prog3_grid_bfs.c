
/*
  Program 3: Grid Pathfinding (BFS) with Obstacles
  - Features: 2D array, BFS queue, boundary checks, while loop, nested if/else,
    multiple assignments to the same variables (good for reaching-defs).
  - No switch/goto; standard C only.
*/
#include <stdio.h>

#define N 10
typedef struct { int r, c; } Node;

typedef struct {
    Node q[N*N];
    int head, tail;
} Queue;

void q_init(Queue *Q){ Q->head = 0; Q->tail = 0; }
int q_empty(Queue *Q){ return Q->head == Q->tail; }
void q_push(Queue *Q, Node v){ Q->q[Q->tail++] = v; }
Node q_pop(Queue *Q){ return Q->q[Q->head++]; }

int in_bounds(int r, int c){ return r>=0 && r<N && c>=0 && c<N; }

int main(void) {
    int grid[N][N];
    int i, j;
    printf("Enter 10x10 grid (0=free,1=wall):\n");
    for (i = 0; i < N; i++) {
        for (j = 0; j < N; j++) {
            if (scanf("%d", &grid[i][j]) != 1) {
                printf("Bad input\n");
                return 0;
            }
            if (grid[i][j] != 0 && grid[i][j] != 1) {
                grid[i][j] = 1; // sanitize: treat invalid as wall
            }
        }
    }

    int sr, sc, tr, tc;
    printf("Enter start r c (0-9 0-9): ");
    if (scanf("%d %d", &sr, &sc) != 2) return 0;
    printf("Enter target r c (0-9 0-9): ");
    if (scanf("%d %d", &tr, &tc) != 2) return 0;

    if (!in_bounds(sr, sc) || !in_bounds(tr, tc)) {
        printf("Out of bounds\n");
        return 0;
    }
    if (grid[sr][sc] == 1 || grid[tr][tc] == 1) {
        printf("Start/target blocked\n");
        return 0;
    }

    int dist[N][N];
    int vis[N][N];
    for (i = 0; i < N; i++) {
        for (j = 0; j < N; j++) {
            dist[i][j] = -1;
            vis[i][j] = 0;
        }
    }

    Queue Q; q_init(&Q);
    q_push(&Q, (Node){sr, sc});
    vis[sr][sc] = 1;
    dist[sr][sc] = 0;

    int dr[4] = {-1, 1, 0, 0};
    int dc[4] = {0, 0, -1, 1};

    while (!q_empty(&Q)) {
        Node u = q_pop(&Q);
        if (u.r == tr && u.c == tc) break;
        for (int k = 0; k < 4; k++) {
            int nr = u.r + dr[k];
            int nc = u.c + dc[k];
            if (in_bounds(nr, nc)) {
                if (!vis[nr][nc] && grid[nr][nc] == 0) {
                    vis[nr][nc] = 1;
                    dist[nr][nc] = dist[u.r][u.c] + 1; // multiple defs of dist
                    q_push(&Q, (Node){nr, nc});
                }
            }
        }
    }

    if (dist[tr][tc] == -1) {
        printf("No path\n");
    } else {
        printf("Shortest path length: %d\n", dist[tr][tc]);
        // Reconstruct one path using greedy neighbor step (not exact BFS parent, for simplicity)
        int r = tr, c = tc;
        int steps = dist[tr][tc];
        while (steps > 0) {
            int found = 0;
            for (int k = 0; k < 4; k++) {
                int pr = r - dr[k];
                int pc = c - dc[k];
                if (in_bounds(pr, pc) && dist[pr][pc] == steps - 1) {
                    r = pr; c = pc; steps = steps - 1;
                    found = 1;
                    break;
                }
            }
            if (!found) break;
        }
        if (r == sr && c == sc && steps == 0) {
            printf("Path check OK\n");
        } else {
            printf("Path reconstruction incomplete (but length is valid)\n");
        }
    }
    return 0;
}
