/*
 * led_blink_short.c  — libgpiod 2.x 최소 구현
 * 빌드: gcc -O2 -o led_blink led_blink_short.c -lgpiod
 * 실행: sudo ./led_blink
 */
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <time.h>
#include <gpiod.h>

#define CHIP     "/dev/gpiochip0"
#define N        3
#define DELAY_MS 1000

static const unsigned int PINS[N] = {16, 20, 21};
static volatile sig_atomic_t running = 1;
static void on_signal(int s) { (void)s; running = 0; }

static void msleep(long ms) {
    nanosleep(&(struct timespec){ms/1000, (ms%1000)*1000000L}, NULL);
}

int main(void) {
    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    struct gpiod_chip         *chip = gpiod_chip_open(CHIP);
    struct gpiod_line_settings *ls  = gpiod_line_settings_new();
    struct gpiod_line_config   *lc  = gpiod_line_config_new();
    struct gpiod_request_config *rc = gpiod_request_config_new();

    if (!chip || !ls || !lc || !rc) { perror("init"); return 1; }

    gpiod_line_settings_set_direction(ls, GPIOD_LINE_DIRECTION_OUTPUT);
    gpiod_line_config_add_line_settings(lc, PINS, N, ls);
    gpiod_request_config_set_consumer(rc, "led");

    struct gpiod_line_request *req = gpiod_chip_request_lines(chip, rc, lc);
    if (!req) { perror("request"); return 1; }

    const enum gpiod_line_value
        ON[N]  = {GPIOD_LINE_VALUE_ACTIVE,   GPIOD_LINE_VALUE_ACTIVE,   GPIOD_LINE_VALUE_ACTIVE},
        OFF[N] = {GPIOD_LINE_VALUE_INACTIVE, GPIOD_LINE_VALUE_INACTIVE, GPIOD_LINE_VALUE_INACTIVE};

    while (running) {
        gpiod_line_request_set_values(req, ON);  msleep(DELAY_MS);
        gpiod_line_request_set_values(req, OFF); msleep(DELAY_MS);
    }

    gpiod_line_request_set_values(req, OFF);
    gpiod_line_request_release(req);
    gpiod_line_config_free(lc);
    gpiod_request_config_free(rc);
    gpiod_line_settings_free(ls);
    gpiod_chip_close(chip);
    return 0;
}
