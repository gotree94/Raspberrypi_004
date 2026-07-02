/*
 * led_blink.c
 * GPIO 16, 20, 21 LED 점멸 (libgpiod 2.x 기반)
 * 빌드: gcc -O2 -o led_blink led_blink.c -lgpiod
 * 실행: sudo ./led_blink
 */

#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <time.h>
#include <gpiod.h>

#define GPIO_CHIP   "/dev/gpiochip0"
#define NUM_LEDS    3
#define BLINK_SEC   1   /* 점멸 간격 (초) */

static const unsigned int LED_PINS[NUM_LEDS] = {16, 20, 21};
static volatile sig_atomic_t keep_running = 1;

static void handle_sigint(int sig)
{
    (void)sig;
    keep_running = 0;
}

static void sleep_ms(long ms)
{
    struct timespec ts = {
        .tv_sec  = ms / 1000,
        .tv_nsec = (ms % 1000) * 1000000L
    };
    nanosleep(&ts, NULL);
}

int main(void)
{
    struct gpiod_chip        *chip   = NULL;
    struct gpiod_line_request *req   = NULL;
    struct gpiod_request_config *rcfg = NULL;
    struct gpiod_line_config    *lcfg = NULL;
    struct gpiod_line_settings  *lset = NULL;
    int ret = EXIT_SUCCESS;

    signal(SIGINT,  handle_sigint);
    signal(SIGTERM, handle_sigint);

    /* 칩 열기 */
    chip = gpiod_chip_open(GPIO_CHIP);
    if (!chip) {
        perror("gpiod_chip_open");
        return EXIT_FAILURE;
    }

    /* 라인 설정: OUTPUT, 초기값 LOW */
    lset = gpiod_line_settings_new();
    if (!lset) { perror("line_settings_new"); ret = EXIT_FAILURE; goto cleanup; }
    gpiod_line_settings_set_direction(lset, GPIOD_LINE_DIRECTION_OUTPUT);
    gpiod_line_settings_set_output_value(lset, GPIOD_LINE_VALUE_INACTIVE);

    lcfg = gpiod_line_config_new();
    if (!lcfg) { perror("line_config_new"); ret = EXIT_FAILURE; goto cleanup; }
    if (gpiod_line_config_add_line_settings(lcfg, LED_PINS, NUM_LEDS, lset) < 0) {
        perror("line_config_add"); ret = EXIT_FAILURE; goto cleanup;
    }

    rcfg = gpiod_request_config_new();
    if (!rcfg) { perror("request_config_new"); ret = EXIT_FAILURE; goto cleanup; }
    gpiod_request_config_set_consumer(rcfg, "led_blink");

    req = gpiod_chip_request_lines(chip, rcfg, lcfg);
    if (!req) { perror("request_lines"); ret = EXIT_FAILURE; goto cleanup; }

    printf("LED 점멸 시작 (GPIO %u, %u, %u) — Ctrl+C 로 종료\n",
           LED_PINS[0], LED_PINS[1], LED_PINS[2]);

    /* 메인 루프 */
    const enum gpiod_line_value ALL_ON[NUM_LEDS]  = {
        GPIOD_LINE_VALUE_ACTIVE,
        GPIOD_LINE_VALUE_ACTIVE,
        GPIOD_LINE_VALUE_ACTIVE
    };
    const enum gpiod_line_value ALL_OFF[NUM_LEDS] = {
        GPIOD_LINE_VALUE_INACTIVE,
        GPIOD_LINE_VALUE_INACTIVE,
        GPIOD_LINE_VALUE_INACTIVE
    };

    while (keep_running) {
        gpiod_line_request_set_values(req, ALL_ON);
        sleep_ms(BLINK_SEC * 1000);
        gpiod_line_request_set_values(req, ALL_OFF);
        sleep_ms(BLINK_SEC * 1000);
    }

    /* 종료 시 LED OFF */
    gpiod_line_request_set_values(req, ALL_OFF);
    printf("\n종료 완료\n");

cleanup:
    if (req)  gpiod_line_request_release(req);
    if (lcfg) gpiod_line_config_free(lcfg);
    if (rcfg) gpiod_request_config_free(rcfg);
    if (lset) gpiod_line_settings_free(lset);
    if (chip) gpiod_chip_close(chip);
    return ret;
}
