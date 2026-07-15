#include "esp_adc/adc_continuous.h"
#include "esp_dsp.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "soc/soc_caps.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

// ==========================================
// CONFIGURATION (ESP32-WROOM-32)
// ==========================================
#define SENSOR_1_PIN ADC_CHANNEL_6 // GPIO34 on WROOM-32 (ADC1)
#define SENSOR_2_PIN ADC_CHANNEL_7 // GPIO35 on WROOM-32 (ADC1)

#define SAMPLING_FREQ 60000
#define SAMPLES 256

const float FREQ_S1 = 12500.0f;
const float FREQ_S2 = 18200.0f;
const float FREQ_MARGIN = 500.0f;

const float TRACK_DISTANCE = 0.5f;  // meters
const float MAG_THRESHOLD = 150.0f; // Adjusted for WROOM noise floor

static const char *TAG = "AXLE_COUNTER";

// ==========================================
// GLOBALS & ARRAYS
// ==========================================
adc_continuous_handle_t adc_handle = NULL;
uint8_t dma_buffer[SAMPLES * 8]; // Larger buffer for safety
TaskHandle_t dsp_task_handle = NULL;

__attribute__((aligned(16))) float v1_complex[512];
__attribute__((aligned(16))) float v2_complex[512];
__attribute__((aligned(16))) float wind_hann[256];

unsigned long tS1 = 0, tS2 = 0;
bool s1Triggered = false, s2Triggered = false;

// ==========================================
// DMA INTERRUPT
// ==========================================
static bool IRAM_ATTR adc_conv_done_cb(adc_continuous_handle_t handle,
                                       const adc_continuous_evt_data_t *edata,
                                       void *user_data) {
  BaseType_t mustYield = pdFALSE;
  vTaskNotifyGiveFromISR(dsp_task_handle, &mustYield);
  return (mustYield == pdTRUE);
}

// ==========================================
// HELPER FUNCTIONS
// ==========================================
float get_peak_in_band(float *complex_data, float target_freq) {
  float max_mag = 0.0f;
  float bin_width = (float)SAMPLING_FREQ / SAMPLES;

  int start_bin = (int)((target_freq - FREQ_MARGIN) / bin_width);
  int end_bin = (int)((target_freq + FREQ_MARGIN) / bin_width);

  for (int i = start_bin; i <= end_bin; i++) {
    if (i >= 0 && i < (SAMPLES / 2)) {
      float re = complex_data[i * 2 + 0];
      float im = complex_data[i * 2 + 1];
      float mag = sqrtf(re * re + im * im);
      if (mag > max_mag) {
        max_mag = mag;
      }
    }
  }
  return max_mag;
}

int total_wheels_detected = 0;
const float DIP_THRESHOLD = 400.0f; // Adjusted for wheel dip

void process_axle_logic(float m1, float m2) {
  unsigned long now = pdTICKS_TO_MS(xTaskGetTickCount());

  if (m1 < DIP_THRESHOLD && !s1Triggered) {
    ESP_LOGD(TAG, "Sensor 1 Hit!");
    tS1 = now;
    s1Triggered = true;
  } else if (m1 > DIP_THRESHOLD + 100.0f) {
    s1Triggered = false;
  }

  if (m2 < DIP_THRESHOLD && !s2Triggered) {
    ESP_LOGD(TAG, "Sensor 2 Hit!");
    tS2 = now;
    s2Triggered = true;
  } else if (m2 > DIP_THRESHOLD + 100.0f) {
    s2Triggered = false;
  }

  if (tS1 > 0 && tS2 > 0) {
    long lag = (long)tS2 - (long)tS1;
    // Prevent divide-by-zero if hit in the same exact millisecond
    if (lag == 0)
      lag = 1;

    float speed = TRACK_DISTANCE / (abs(lag) / 1000.0f);
    total_wheels_detected++;

    ESP_LOGI(TAG, ">> AXLE EVENT DETECTED <<");
    ESP_LOGI(TAG, "Direction: %s | Lag: %ld ms | Speed: %.2f m/s",
             (lag > 0 ? "INCOMING" : "OUTGOING"), abs(lag), speed);
    ESP_LOGI(TAG, "Total Wheels Detected: %d", total_wheels_detected);

    tS1 = 0;
    tS2 = 0;
  }
}

// ==========================================
// CORE 1 DSP TASK
// ==========================================
void dsp_processing_task(void *parameter) {
  uint32_t ret_num = 0;

  while (1) {
    ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

    esp_err_t ret = adc_continuous_read(adc_handle, dma_buffer,
                                        sizeof(dma_buffer), &ret_num, 0);

    if (ret == ESP_OK) {
      int s1_idx = 0;
      int s2_idx = 0;

      // ESP32 WROOM Uses Type1 Format (SOC_ADC_DIGI_RESULT_BYTES = 2 bytes)
      for (int i = 0; i < ret_num; i += SOC_ADC_DIGI_RESULT_BYTES) {
        adc_digi_output_data_t *p = (adc_digi_output_data_t *)&dma_buffer[i];

        // Subtract 2048 to remove the DC offset from the 0-3.3V digital square
        // wave
        if (p->type1.channel == SENSOR_1_PIN && s1_idx < SAMPLES) {
          v1_complex[s1_idx * 2 + 0] =
              ((float)(p->type1.data) - 2048.0f) * wind_hann[s1_idx];
          v1_complex[s1_idx * 2 + 1] = 0.0f;
          s1_idx++;
        } else if (p->type1.channel == SENSOR_2_PIN && s2_idx < SAMPLES) {
          v2_complex[s2_idx * 2 + 0] =
              ((float)(p->type1.data) - 2048.0f) * wind_hann[s2_idx];
          v2_complex[s2_idx * 2 + 1] = 0.0f;
          s2_idx++;
        }
      }

      // If we didn't fill the arrays, skip this cycle
      if (s1_idx < SAMPLES || s2_idx < SAMPLES)
        continue;

      // --- ESP-DSP FFT Calculation ---
      dsps_fft2r_fc32(v1_complex, SAMPLES);
      dsps_bit_rev_fc32(v1_complex, SAMPLES);

      dsps_fft2r_fc32(v2_complex, SAMPLES);
      dsps_bit_rev_fc32(v2_complex, SAMPLES);

      float magS1 = get_peak_in_band(v1_complex, FREQ_S1);
      float magS2 = get_peak_in_band(v2_complex, FREQ_S2);

      // Print diagnostics and plot ASCII graph!
      static int log_divider = 0;
      if (log_divider++ % 2 == 0) {
        int bars_s1 = (int)(magS1 / 20.0f);
        if (bars_s1 > 40) bars_s1 = 40;
        if (bars_s1 < 0) bars_s1 = 0;
        
        int bars_s2 = (int)(magS2 / 20.0f);
        if (bars_s2 > 40) bars_s2 = 40;
        if (bars_s2 < 0) bars_s2 = 0;

        char bar1[41] = {0};
        char bar2[41] = {0};
        memset(bar1, '#', bars_s1);
        memset(bar2, '*', bars_s2);

        unsigned long now = pdTICKS_TO_MS(xTaskGetTickCount());
        ESP_LOGI("GRAPH", "T:%4ld | S1:%6.1f %-40s | S2:%6.1f %-40s", 
                 now, magS1, bar1, magS2, bar2);
      }

      process_axle_logic(magS1, magS2);
    }
  }
}

// ==========================================
// MAIN ENTRY POINT
// ==========================================
void app_main(void) {
  ESP_LOGI(TAG, "Booting Industrial DMA Axle Counter (WROOM-32)...");

  esp_err_t dsp_ret = dsps_fft2r_init_fc32(NULL, CONFIG_DSP_MAX_FFT_SIZE);
  if (dsp_ret != ESP_OK) {
    ESP_LOGE(TAG, "Not possible to initialize FFT. Error = %i", dsp_ret);
    return;
  }
  dsps_wind_hann_f32(wind_hann, SAMPLES);

  adc_continuous_handle_cfg_t adc_config = {
      .max_store_buf_size = 2048,
      .conv_frame_size = SAMPLES * SOC_ADC_DIGI_RESULT_BYTES * 2,
  };
  ESP_ERROR_CHECK(adc_continuous_new_handle(&adc_config, &adc_handle));

  adc_continuous_config_t dig_cfg = {
      .sample_freq_hz = SAMPLING_FREQ,
      .conv_mode = ADC_CONV_SINGLE_UNIT_1,    // ESP32 ADC1
      .format = ADC_DIGI_OUTPUT_FORMAT_TYPE1, // WROOM specific!
  };

  adc_digi_pattern_config_t adc_pattern[2] = {0};

  adc_pattern[0].atten = ADC_ATTEN_DB_12;
  adc_pattern[0].channel = SENSOR_1_PIN;
  adc_pattern[0].unit = ADC_UNIT_1;
  adc_pattern[0].bit_width = SOC_ADC_DIGI_MAX_BITWIDTH;

  adc_pattern[1].atten = ADC_ATTEN_DB_12;
  adc_pattern[1].channel = SENSOR_2_PIN;
  adc_pattern[1].unit = ADC_UNIT_1;
  adc_pattern[1].bit_width = SOC_ADC_DIGI_MAX_BITWIDTH;

  dig_cfg.pattern_num = 2;
  dig_cfg.adc_pattern = adc_pattern;
  ESP_ERROR_CHECK(adc_continuous_config(adc_handle, &dig_cfg));

  adc_continuous_evt_cbs_t cbs = {.on_conv_done = adc_conv_done_cb};
  ESP_ERROR_CHECK(
      adc_continuous_register_event_callbacks(adc_handle, &cbs, NULL));

  xTaskCreatePinnedToCore(dsp_processing_task, "DSP_Task", 1024 * 8, NULL, 5,
                          &dsp_task_handle, 1);

  ESP_ERROR_CHECK(adc_continuous_start(adc_handle));
  ESP_LOGI(TAG, "DMA Hardware Started. CPU 0 is free. CPU 1 is ready.");
}