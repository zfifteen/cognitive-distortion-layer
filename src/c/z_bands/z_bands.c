#include <errno.h>
#include <limits.h>
#include <mpfr.h>
#include <gmp.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define ARRAY_LEN(x) (sizeof(x) / sizeof((x)[0]))
#define MAX_FACTORS 6
#define MAX_VECTOR_TEXT 64
#define MAX_STATUS_TEXT 64
#define MAX_SCI_TEXT 96
#define MAX_FIXED_TEXT 96
#define SAME_DIGIT_RETRY_LIMIT 12
#define DEFAULT_MIN_DIGITS 1
#define DEFAULT_MAX_DIGITS 32
#define DEFAULT_SAMPLES_PER_BAND 1UL
#define DEFAULT_FULL_MIN_DIGITS 1
#define DEFAULT_FULL_MAX_DIGITS 1234
#define DEFAULT_FULL_SAMPLES_PER_BAND 128UL
#define DEFAULT_PROBABLE_PRIME_REPS 64UL
#define DEFAULT_PRECISION 8192
#define DEFAULT_OUT_DIR "artifacts/reports/z_bands"
#define LEAD_TAIL_WIDTH 16
#define SPOT_CHECK_SMALL_FACTOR_BOUND 10000
#define SPOT_CHECK_SMALL_FACTOR_ROWS 8

typedef struct {
    const char *name;
    size_t factor_count;
    unsigned long exponents[MAX_FACTORS];
    unsigned long d_value;
} family_spec_t;

typedef struct {
    int min_digits;
    int min_factor_digits[MAX_FACTORS];
} family_support_t;

typedef struct {
    int min_digits;
    int max_digits;
    unsigned long samples_per_band;
    const char *out_dir;
    unsigned long probable_prime_reps;
    mpfr_prec_t precision;
    bool spot_check_factor;
    bool check_mode;
} run_config_t;

typedef struct {
    bool valid;
    int band_digits;
    const char *family_name;
    unsigned long sample_index;
    unsigned long d_value;
    char exponent_vector[MAX_VECTOR_TEXT];
    char factor_digit_lengths[MAX_VECTOR_TEXT];
    char leading16[LEAD_TAIL_WIDTH + 1];
    char trailing16[LEAD_TAIL_WIDTH + 1];
    char z_sci[MAX_SCI_TEXT];
    char neg_log10_z[MAX_FIXED_TEXT];
    long double neg_log10_value;
    char status[MAX_STATUS_TEXT];
} sample_snapshot_t;

typedef struct {
    bool ok;
    int band_digits;
    unsigned long d_value;
    int factor_digits[MAX_FACTORS];
    int n_digits;
    unsigned long n_bits;
    char exponent_vector[MAX_VECTOR_TEXT];
    char factor_digit_lengths[MAX_VECTOR_TEXT];
    char n_log10[MAX_FIXED_TEXT];
    char leading16[LEAD_TAIL_WIDTH + 1];
    char trailing16[LEAD_TAIL_WIDTH + 1];
    char z_sci[MAX_SCI_TEXT];
    char neg_log10_z[MAX_FIXED_TEXT];
    long double neg_log10_value;
    char status[MAX_STATUS_TEXT];
} sample_result_t;

typedef struct {
    unsigned long total_band_rows;
    unsigned long supported_band_rows;
    unsigned long unsupported_band_rows;
    unsigned long total_samples_requested;
    unsigned long total_samples_built;
    unsigned long probable_prime_fixed_points;
    unsigned long probable_prime_total;
    unsigned long composite_subunit_count;
    unsigned long composite_total;
    sample_snapshot_t strongest_composite;
    sample_snapshot_t weakest_composite;
} summary_stats_t;

typedef struct {
    unsigned long total_samples;
    unsigned long factors_found;
    unsigned long factor_missing;
    unsigned long smallest_factor_found;
    bool has_smallest_factor;
    sample_snapshot_t first_factor_found;
    sample_snapshot_t first_factor_missing;
} spot_summary_t;

static const family_spec_t FAMILY_SPECS[] = {
    { "probable_prime", 1, {1, 0, 0, 0, 0, 0}, 2 },
    { "semiprime_balanced", 2, {1, 1, 0, 0, 0, 0}, 4 },
    { "prime_square", 1, {2, 0, 0, 0, 0, 0}, 3 },
    { "prime_cube", 1, {3, 0, 0, 0, 0, 0}, 4 },
    { "squarefree_3", 3, {1, 1, 1, 0, 0, 0}, 8 },
    { "squarefree_6", 6, {1, 1, 1, 1, 1, 1}, 64 },
    { "smooth_4321", 4, {4, 3, 2, 1, 0, 0}, 120 },
};

static void multiply_prime_powers(mpz_t out, const family_spec_t *family, mpz_t *primes);
static void compute_sample_metrics(const family_spec_t *family, mpz_t n, int *factor_digits, sample_result_t *sample, mpfr_prec_t precision);
static bool generate_probable_prime_exact_digits(mpz_t out, int digits, mpz_t *pow10, mpz_t *existing, size_t existing_count, unsigned long probable_prime_reps, unsigned long ordinal);

static const char *family_description(const char *name) {
    if (strcmp(name, "probable_prime") == 0) {
        return "Single probable prime; the exact fixed-point family with d(n)=2.";
    }
    if (strcmp(name, "semiprime_balanced") == 0) {
        return "Product of two distinct primes with matched scale; the basic semiprime family.";
    }
    if (strcmp(name, "prime_square") == 0) {
        return "Square of a prime; the simplest prime-power composite family.";
    }
    if (strcmp(name, "prime_cube") == 0) {
        return "Cube of a prime; a higher-curvature prime-power composite family.";
    }
    if (strcmp(name, "squarefree_3") == 0) {
        return "Product of three distinct primes; a low-multiplicity squarefree composite family.";
    }
    if (strcmp(name, "squarefree_6") == 0) {
        return "Product of six distinct primes; a higher-divisor squarefree composite family.";
    }
    if (strcmp(name, "smooth_4321") == 0) {
        return "Composite with exponent pattern 4,3,2,1; a smooth high-divisor family.";
    }
    return "Exact known-factorization family.";
}

static void fatalf(const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    vfprintf(stderr, fmt, args);
    va_end(args);
    fputc('\n', stderr);
    exit(EXIT_FAILURE);
}

static void *xmalloc(size_t size) {
    void *ptr = malloc(size);
    if (ptr == NULL) {
        fatalf("out of memory");
    }
    return ptr;
}

static void free_gmp_string(char *text) {
    void (*freefunc)(void *, size_t) = NULL;
    if (text == NULL) {
        return;
    }
    mp_get_memory_functions(NULL, NULL, &freefunc);
    freefunc(text, strlen(text) + 1U);
}

static void build_vector_text(const unsigned long *values, size_t count, char *buffer, size_t buffer_size) {
    size_t offset = 0;
    buffer[0] = '\0';
    for (size_t i = 0; i < count; ++i) {
        int written = snprintf(buffer + offset, buffer_size - offset, "%s%lu", i == 0 ? "" : ",", values[i]);
        if (written < 0 || (size_t) written >= buffer_size - offset) {
            fatalf("vector text buffer too small");
        }
        offset += (size_t) written;
    }
}

static void build_int_vector_text(const int *values, size_t count, char *buffer, size_t buffer_size) {
    size_t offset = 0;
    buffer[0] = '\0';
    for (size_t i = 0; i < count; ++i) {
        int written = snprintf(buffer + offset, buffer_size - offset, "%s%d", i == 0 ? "" : ",", values[i]);
        if (written < 0 || (size_t) written >= buffer_size - offset) {
            fatalf("vector text buffer too small");
        }
        offset += (size_t) written;
    }
}

static void copy_slice(const char *source, size_t start, size_t len, char *out, size_t out_size) {
    if (len + 1 > out_size) {
        fatalf("slice buffer too small");
    }
    memcpy(out, source + start, len);
    out[len] = '\0';
}

static void init_pow10_table(mpz_t **table_out, int max_digits) {
    mpz_t *table = xmalloc((size_t) (max_digits + 1) * sizeof(mpz_t));
    for (int i = 0; i <= max_digits; ++i) {
        mpz_init(table[i]);
    }
    mpz_set_ui(table[0], 1);
    for (int i = 1; i <= max_digits; ++i) {
        mpz_mul_ui(table[i], table[i - 1], 10UL);
    }
    *table_out = table;
}

static void clear_pow10_table(mpz_t *table, int max_digits) {
    for (int i = 0; i <= max_digits; ++i) {
        mpz_clear(table[i]);
    }
    free(table);
}

static void init_summary(summary_stats_t *summary) {
    memset(summary, 0, sizeof(*summary));
    summary->strongest_composite.neg_log10_value = -1.0L;
    summary->weakest_composite.neg_log10_value = 1.0e300L;
}

static void update_extreme(sample_snapshot_t *slot, const sample_result_t *sample, const family_spec_t *family, unsigned long sample_index) {
    slot->valid = true;
    slot->band_digits = sample->band_digits;
    slot->family_name = family->name;
    slot->sample_index = sample_index;
    slot->d_value = sample->d_value;
    snprintf(slot->exponent_vector, sizeof(slot->exponent_vector), "%s", sample->exponent_vector);
    snprintf(slot->factor_digit_lengths, sizeof(slot->factor_digit_lengths), "%s", sample->factor_digit_lengths);
    snprintf(slot->leading16, sizeof(slot->leading16), "%s", sample->leading16);
    snprintf(slot->trailing16, sizeof(slot->trailing16), "%s", sample->trailing16);
    snprintf(slot->z_sci, sizeof(slot->z_sci), "%s", sample->z_sci);
    snprintf(slot->neg_log10_z, sizeof(slot->neg_log10_z), "%s", sample->neg_log10_z);
    snprintf(slot->status, sizeof(slot->status), "%s", sample->status);
    slot->neg_log10_value = sample->neg_log10_value;
}

static void summary_note_sample(summary_stats_t *summary, const sample_result_t *sample, const family_spec_t *family, unsigned long sample_index) {
    if (strcmp(family->name, "probable_prime") == 0) {
        summary->probable_prime_total += 1;
        if (strcmp(sample->z_sci, "1") == 0) {
            summary->probable_prime_fixed_points += 1;
        }
        return;
    }

    summary->composite_total += 1;
    if (sample->neg_log10_value > 0.0L) {
        summary->composite_subunit_count += 1;
    }
    if (!summary->strongest_composite.valid || sample->neg_log10_value > summary->strongest_composite.neg_log10_value) {
        update_extreme(&summary->strongest_composite, sample, family, sample_index);
    }
    if (!summary->weakest_composite.valid || sample->neg_log10_value < summary->weakest_composite.neg_log10_value) {
        update_extreme(&summary->weakest_composite, sample, family, sample_index);
    }
}

static void format_fixed_mpfr(mpfr_t value, char *out, size_t out_size) {
    if (mpfr_snprintf(out, out_size, "%.24Rf", value) < 0) {
        fatalf("failed to format MPFR value");
    }
}

static void format_fixed_long_double(long double value, char *out, size_t out_size) {
    if (snprintf(out, out_size, "%.24Lf", value) < 0) {
        fatalf("failed to format floating value");
    }
}

static void format_z_scientific_from_neg(mpfr_t neg_log10_z, char *out, size_t out_size) {
    if (mpfr_zero_p(neg_log10_z)) {
        snprintf(out, out_size, "1");
        return;
    }

    mpfr_t floor_part;
    mpfr_t frac_part;
    mpfr_t one_minus_frac;
    mpfr_t mantissa;
    mpfr_init2(floor_part, mpfr_get_prec(neg_log10_z));
    mpfr_init2(frac_part, mpfr_get_prec(neg_log10_z));
    mpfr_init2(one_minus_frac, mpfr_get_prec(neg_log10_z));
    mpfr_init2(mantissa, mpfr_get_prec(neg_log10_z));

    mpfr_floor(floor_part, neg_log10_z);
    mpfr_frac(frac_part, neg_log10_z, MPFR_RNDN);

    unsigned long exponent = mpfr_get_ui(floor_part, MPFR_RNDN);
    if (mpfr_zero_p(frac_part)) {
        if (snprintf(out, out_size, "1e-%lu", exponent) < 0) {
            fatalf("failed to format scientific value");
        }
    } else {
        char mantissa_text[64];
        mpfr_ui_sub(one_minus_frac, 1UL, frac_part, MPFR_RNDN);
        mpfr_exp10(mantissa, one_minus_frac, MPFR_RNDN);
        if (mpfr_snprintf(mantissa_text, sizeof(mantissa_text), "%.24Rf", mantissa) < 0) {
            fatalf("failed to format mantissa");
        }
        if (snprintf(out, out_size, "%se-%lu", mantissa_text, exponent + 1UL) < 0) {
            fatalf("failed to format scientific value");
        }
    }

    mpfr_clear(floor_part);
    mpfr_clear(frac_part);
    mpfr_clear(one_minus_frac);
    mpfr_clear(mantissa);
}

static void compute_number_features(mpz_t n, char *leading16, char *trailing16, int *digits_out, unsigned long *bits_out) {
    char *decimal = mpz_get_str(NULL, 10, n);
    size_t length = strlen(decimal);

    *digits_out = (int) length;
    *bits_out = mpz_sizeinbase(n, 2);

    size_t leading_len = length < LEAD_TAIL_WIDTH ? length : LEAD_TAIL_WIDTH;
    size_t trailing_len = length < LEAD_TAIL_WIDTH ? length : LEAD_TAIL_WIDTH;

    copy_slice(decimal, 0, leading_len, leading16, LEAD_TAIL_WIDTH + 1);
    copy_slice(decimal, length - trailing_len, trailing_len, trailing16, LEAD_TAIL_WIDTH + 1);

    free_gmp_string(decimal);
}

static int compare_long_double(const void *lhs, const void *rhs) {
    long double a = *(const long double *) lhs;
    long double b = *(const long double *) rhs;
    if (a < b) {
        return -1;
    }
    if (a > b) {
        return 1;
    }
    return 0;
}

static long double compute_median(long double *values, size_t count) {
    if (count == 0) {
        return 0.0L;
    }
    qsort(values, count, sizeof(long double), compare_long_double);
    if ((count & 1U) == 1U) {
        return values[count / 2];
    }
    return (values[count / 2 - 1] + values[count / 2]) / 2.0L;
}

static void ensure_directory(const char *path) {
    char buffer[PATH_MAX];
    size_t length = strlen(path);

    if (length >= sizeof(buffer)) {
        fatalf("path too long: %s", path);
    }

    snprintf(buffer, sizeof(buffer), "%s", path);
    for (size_t i = 1; i < length; ++i) {
        if (buffer[i] == '/') {
            buffer[i] = '\0';
            if (mkdir(buffer, 0775) != 0 && errno != EEXIST) {
                fatalf("failed to create directory %s: %s", buffer, strerror(errno));
            }
            buffer[i] = '/';
        }
    }
    if (mkdir(buffer, 0775) != 0 && errno != EEXIST) {
        fatalf("failed to create directory %s: %s", buffer, strerror(errno));
    }
}

static FILE *open_output_file(const char *dir, const char *name) {
    char path[PATH_MAX];
    if (snprintf(path, sizeof(path), "%s/%s", dir, name) < 0) {
        fatalf("failed to construct output path");
    }
    FILE *file = fopen(path, "w");
    if (file == NULL) {
        fatalf("failed to open %s: %s", path, strerror(errno));
    }
    return file;
}

static void write_samples_header(FILE *file) {
    fprintf(file, "band_digits,family,sample_index,probable_prime_reps,exponent_vector,factor_digit_lengths,d_value,n_digits,n_bits,n_log10,leading16,trailing16,z_sci,neg_log10_z,status\n");
}

static void write_bands_header(FILE *file) {
    fprintf(file, "band_digits,family,supported,samples_requested,samples_built,d_value,unit_z_count,subunit_z_count,min_neg_log10_z,median_neg_log10_z,max_neg_log10_z,status\n");
}

static void write_sample_row(FILE *file, const family_spec_t *family, const sample_result_t *sample, const run_config_t *config, unsigned long sample_index) {
    fprintf(
        file,
        "%d,%s,%lu,%lu,\"%s\",\"%s\",%lu,%d,%lu,%s,%s,%s,%s,%s,%s\n",
        sample->band_digits,
        family->name,
        sample_index,
        config->probable_prime_reps,
        sample->exponent_vector,
        sample->factor_digit_lengths,
        sample->d_value,
        sample->n_digits,
        sample->n_bits,
        sample->n_log10,
        sample->leading16,
        sample->trailing16,
        sample->z_sci,
        sample->neg_log10_z,
        sample->status
    );
}

static void write_band_row(
    FILE *file,
    int band_digits,
    const family_spec_t *family,
    bool supported,
    unsigned long samples_requested,
    unsigned long samples_built,
    unsigned long unit_z_count,
    unsigned long subunit_z_count,
    long double min_neg,
    long double median_neg,
    long double max_neg,
    const char *status
) {
    char min_text[MAX_FIXED_TEXT];
    char median_text[MAX_FIXED_TEXT];
    char max_text[MAX_FIXED_TEXT];
    format_fixed_long_double(min_neg, min_text, sizeof(min_text));
    format_fixed_long_double(median_neg, median_text, sizeof(median_text));
    format_fixed_long_double(max_neg, max_text, sizeof(max_text));

    fprintf(
        file,
        "%d,%s,%s,%lu,%lu,%lu,%lu,%lu,%s,%s,%s,%s\n",
        band_digits,
        family->name,
        supported ? "true" : "false",
        samples_requested,
        samples_built,
        family->d_value,
        unit_z_count,
        subunit_z_count,
        min_text,
        median_text,
        max_text,
        status
    );
}

static void write_main_summary(FILE *file, const run_config_t *config, const family_support_t *support, const summary_stats_t *summary) {
    fprintf(file, "# Z-Bands Summary\n\n");
    fprintf(file, "## Methodology\n\n");
    fprintf(file, "- Platform: Apple Silicon only (`Darwin arm64`).\n");
    fprintf(file, "- Arithmetic stack: C99 with GMP and MPFR only.\n");
    fprintf(file, "- Construction path: fully deterministic, with no random generation and no fallback branches.\n");
    fprintf(file, "- Study mode: exact known-factorization families across decimal digit bands `%d..%d`.\n", config->min_digits, config->max_digits);
    fprintf(file, "- Samples per band and family: `%lu`.\n", config->samples_per_band);
    fprintf(file, "- Per band-family pair, the harness emits a canonical deterministic construction replicated across the requested sample rows.\n");
    fprintf(file, "- MPFR precision: `%lu` bits.\n", (unsigned long) config->precision);
    fprintf(file, "- Probable-prime repetitions: `%lu`.\n\n", config->probable_prime_reps);

    fprintf(file, "## Mathematical Method\n\n");
    fprintf(file, "For each constructed integer `n`, the harness studies the divisor-count transform\n");
    fprintf(file, "`Z(n) = n^(1 - d(n)/2)`, where `d(n)` is the number of positive divisors of `n`.\n\n");
    fprintf(file, "This is the numerically stable closed form of the equivalent exponential expression\n");
    fprintf(file, "`Z(n) = n / exp(v * d(n) * ln(n) / e^2)` with `v = e^2 / 2`.\n\n");
    fprintf(file, "The key structural property is:\n\n");
    fprintf(file, "- If `d(n) = 2`, then `n` is prime and `Z(n) = 1` exactly.\n");
    fprintf(file, "- If `d(n) > 2`, then `n` is composite and `Z(n) < 1`.\n\n");
    fprintf(file, "This harness does not scan every integer in a range. Instead, it constructs representative\n");
    fprintf(file, "integers from exact factorization families. If `n = prod p_i^a_i`, then the divisor count is\n");
    fprintf(file, "`d(n) = prod (a_i + 1)`. Each family therefore fixes the divisor-count regime in advance and\n");
    fprintf(file, "lets the run compare how the same transform behaves across increasing digit bands.\n\n");

    fprintf(file, "## Family Definitions\n\n");
    fprintf(file, "| Family | Description | Exponents | d(n) | Minimum supported digits |\n");
    fprintf(file, "|---|---|---|---:|---:|\n");
    for (size_t i = 0; i < ARRAY_LEN(FAMILY_SPECS); ++i) {
        char vector_text[MAX_VECTOR_TEXT];
        build_vector_text(FAMILY_SPECS[i].exponents, FAMILY_SPECS[i].factor_count, vector_text, sizeof(vector_text));
        fprintf(
            file,
            "| `%s` | %s | `%s` | `%lu` | `%d` |\n",
            FAMILY_SPECS[i].name,
            family_description(FAMILY_SPECS[i].name),
            vector_text,
            FAMILY_SPECS[i].d_value,
            support[i].min_digits
        );
    }
    fprintf(file, "\n");

    fprintf(file, "## How to Read the Outputs\n\n");
    fprintf(file, "- `samples.csv` contains one row per emitted sample. Each row records the band, family, divisor count,\n");
    fprintf(file, "  the sampled integer's size metadata, and the transform outputs `Z(n)` and `-log10(Z)`.\n");
    fprintf(file, "- `bands.csv` aggregates those sample rows by band and family, including support status and contraction statistics.\n");
    fprintf(file, "- `z_sci` is the scientific-notation rendering of `Z(n)`.\n");
    fprintf(file, "- `neg_log10_z` is the contraction depth. Larger values mean smaller `Z(n)` and therefore stronger composite contraction.\n");
    fprintf(file, "- In this experiment, rows labeled `probable_prime` are fixed-point rows (`Z = 1`), while the composite families are contraction rows (`Z < 1`).\n\n");

    fprintf(file, "## Run Configuration\n\n");
    fprintf(file, "- Total band rows: `%lu`\n", summary->total_band_rows);
    fprintf(file, "- Supported band rows: `%lu`\n", summary->supported_band_rows);
    fprintf(file, "- Unsupported band rows: `%lu`\n", summary->unsupported_band_rows);
    fprintf(file, "- Total samples requested: `%lu`\n", summary->total_samples_requested);
    fprintf(file, "- Total samples built: `%lu`\n\n", summary->total_samples_built);

    fprintf(file, "## Results\n\n");
    fprintf(file, "- Probable-prime fixed points: `%lu / %lu` rows emitted `Z = 1` exactly.\n", summary->probable_prime_fixed_points, summary->probable_prime_total);
    fprintf(file, "- Composite strict contractions: `%lu / %lu` rows emitted `-log10(Z) > 0`.\n", summary->composite_subunit_count, summary->composite_total);
    fprintf(file, "- Supported coverage was emitted for every band-family pair with `band_digits >= minimum supported digits`.\n\n");

    fprintf(file, "## Highlighted Examples\n\n");
    if (summary->weakest_composite.valid) {
        fprintf(file, "### Composite Closest to the Fixed Point\n\n");
        fprintf(file, "- Family: `%s`\n", summary->weakest_composite.family_name);
        fprintf(file, "- Band: `%d`\n", summary->weakest_composite.band_digits);
        fprintf(file, "- Sample index: `%lu`\n", summary->weakest_composite.sample_index);
        fprintf(file, "- d(n): `%lu`\n", summary->weakest_composite.d_value);
        fprintf(file, "- Factor digit lengths: `%s`\n", summary->weakest_composite.factor_digit_lengths);
        fprintf(file, "- Leading16: `%s`\n", summary->weakest_composite.leading16);
        fprintf(file, "- Trailing16: `%s`\n", summary->weakest_composite.trailing16);
        fprintf(file, "- Z(n): `%s`\n", summary->weakest_composite.z_sci);
        fprintf(file, "- -log10(Z): `%s`\n\n", summary->weakest_composite.neg_log10_z);
    }

    if (summary->strongest_composite.valid) {
        fprintf(file, "### Deepest Composite Contraction\n\n");
        fprintf(file, "- Family: `%s`\n", summary->strongest_composite.family_name);
        fprintf(file, "- Band: `%d`\n", summary->strongest_composite.band_digits);
        fprintf(file, "- Sample index: `%lu`\n", summary->strongest_composite.sample_index);
        fprintf(file, "- d(n): `%lu`\n", summary->strongest_composite.d_value);
        fprintf(file, "- Factor digit lengths: `%s`\n", summary->strongest_composite.factor_digit_lengths);
        fprintf(file, "- Leading16: `%s`\n", summary->strongest_composite.leading16);
        fprintf(file, "- Trailing16: `%s`\n", summary->strongest_composite.trailing16);
        fprintf(file, "- Z(n): `%s`\n", summary->strongest_composite.z_sci);
        fprintf(file, "- -log10(Z): `%s`\n\n", summary->strongest_composite.neg_log10_z);
    }
}

static void write_main_summary_stub(FILE *file, const run_config_t *config) {
    fprintf(file, "# Z-Bands Summary\n\n");
    fprintf(file, "Status: run_in_progress\n\n");
    fprintf(file, "- Platform: Apple Silicon only (`Darwin arm64`).\n");
    fprintf(file, "- Arithmetic stack: C99 with GMP and MPFR only.\n");
    fprintf(file, "- Construction path: fully deterministic, with no random generation and no fallback branches.\n");
    fprintf(file, "- Digit bands: `%d..%d`.\n", config->min_digits, config->max_digits);
    fprintf(file, "- Samples per band and family: `%lu`.\n", config->samples_per_band);
    fprintf(file, "- MPFR precision: `%lu` bits.\n", (unsigned long) config->precision);
    fprintf(file, "- Probable-prime repetitions: `%lu`.\n\n", config->probable_prime_reps);
    fprintf(file, "The final summary adds mathematical context, output interpretation notes, and run statistics after all band-family rows complete.\n");
}

static void write_spot_samples_header(FILE *file) {
    fprintf(file, "band_digits,sample_index,n_digits,n_bits,n_log10,leading16,trailing16,small_factor,status\n");
}

static void write_spot_bands_header(FILE *file) {
    fprintf(file, "band_digits,samples_requested,samples_built,factors_found,factor_missing,smallest_factor_found,status\n");
}

static void write_spot_summary(FILE *file, const run_config_t *config, const spot_summary_t *summary) {
    fprintf(file, "# Z-Bands Spot Check Summary\n\n");
    fprintf(file, "## Methodology\n\n");
    fprintf(file, "- Mode: bounded small-factor spot check.\n");
    fprintf(file, "- Construction path: fully deterministic, with no random generation and no fallback branches.\n");
    fprintf(file, "- Digit bands: `%d..%d`.\n", config->min_digits, config->max_digits);
    fprintf(file, "- Samples per band: `%lu`.\n", config->samples_per_band);
    fprintf(file, "- Small-factor bound: `%d`.\n\n", SPOT_CHECK_SMALL_FACTOR_BOUND);

    fprintf(file, "## Results\n\n");
    fprintf(file, "- Total sampled odd integers: `%lu`\n", summary->total_samples);
    fprintf(file, "- Samples with a factor <= `%d`: `%lu`\n", SPOT_CHECK_SMALL_FACTOR_BOUND, summary->factors_found);
    fprintf(file, "- Samples with no factor <= `%d`: `%lu`\n\n", SPOT_CHECK_SMALL_FACTOR_BOUND, summary->factor_missing);

    if (summary->has_smallest_factor) {
        fprintf(file, "## First Small-Factor Hit\n\n");
        fprintf(file, "- Band: `%d`\n", summary->first_factor_found.band_digits);
        fprintf(file, "- Sample index: `%lu`\n", summary->first_factor_found.sample_index);
        fprintf(file, "- Leading16: `%s`\n", summary->first_factor_found.leading16);
        fprintf(file, "- Trailing16: `%s`\n", summary->first_factor_found.trailing16);
        fprintf(file, "- Status: `%s`\n\n", summary->first_factor_found.status);
    }

    if (summary->first_factor_missing.valid) {
        fprintf(file, "## First No-Factor Sample\n\n");
        fprintf(file, "- Band: `%d`\n", summary->first_factor_missing.band_digits);
        fprintf(file, "- Sample index: `%lu`\n", summary->first_factor_missing.sample_index);
        fprintf(file, "- Leading16: `%s`\n", summary->first_factor_missing.leading16);
        fprintf(file, "- Trailing16: `%s`\n", summary->first_factor_missing.trailing16);
        fprintf(file, "- Status: `%s`\n\n", summary->first_factor_missing.status);
    }
}

static void write_spot_summary_stub(FILE *file, const run_config_t *config) {
    fprintf(file, "# Z-Bands Spot Check Summary\n\n");
    fprintf(file, "Status: run_in_progress\n\n");
    fprintf(file, "- Mode: bounded small-factor spot check.\n");
    fprintf(file, "- Construction path: fully deterministic, with no random generation and no fallback branches.\n");
    fprintf(file, "- Digit bands: `%d..%d`.\n", config->min_digits, config->max_digits);
    fprintf(file, "- Samples per band: `%lu`.\n", config->samples_per_band);
    fprintf(file, "- Small-factor bound: `%d`.\n\n", SPOT_CHECK_SMALL_FACTOR_BOUND);
    fprintf(file, "The final summary is written after the spot-check sweep completes.\n");
}

static void compute_min_support(const family_spec_t *family, family_support_t *support) {
    static const unsigned long smallest_primes[] = {2UL, 3UL, 5UL, 7UL, 11UL, 13UL};
    mpz_t value;
    mpz_t factor_power;

    mpz_init_set_ui(value, 1UL);
    mpz_init(factor_power);

    for (size_t i = 0; i < family->factor_count; ++i) {
        char prime_text[32];
        snprintf(prime_text, sizeof(prime_text), "%lu", smallest_primes[i]);
        support->min_factor_digits[i] = (int) strlen(prime_text);
        mpz_ui_pow_ui(factor_power, smallest_primes[i], family->exponents[i]);
        mpz_mul(value, value, factor_power);
    }

    {
        char *decimal = mpz_get_str(NULL, 10, value);
        support->min_digits = (int) strlen(decimal);
        free_gmp_string(decimal);
    }

    mpz_clear(value);
    mpz_clear(factor_power);
}

static void build_all_support(family_support_t *support) {
    for (size_t i = 0; i < ARRAY_LEN(FAMILY_SPECS); ++i) {
        memset(&support[i], 0, sizeof(support[i]));
        compute_min_support(&FAMILY_SPECS[i], &support[i]);
    }
}

static void initialize_factor_targets(const family_spec_t *family, const family_support_t *support, int band_digits, int *factor_digits) {
    long double target_log = (long double) band_digits - 0.5L;
    for (size_t i = 0; i < family->factor_count; ++i) {
        long double ideal = target_log / ((long double) family->factor_count * (long double) family->exponents[i]);
        int digits = (int) ideal + 1;
        if (digits < support->min_factor_digits[i]) {
            digits = support->min_factor_digits[i];
        }
        factor_digits[i] = digits;
    }
}

static size_t pick_adjustment_index(const family_spec_t *family, const family_support_t *support, const int *factor_digits, bool increase) {
    size_t best = 0;
    for (size_t i = 1; i < family->factor_count; ++i) {
        bool better = false;
        if (!increase && factor_digits[i] <= support->min_factor_digits[i]) {
            continue;
        }
        if (!increase && factor_digits[best] <= support->min_factor_digits[best]) {
            better = true;
        } else if (family->exponents[i] < family->exponents[best]) {
            better = true;
        } else if (family->exponents[i] == family->exponents[best] && i > best) {
            better = true;
        }
        if (better) {
            best = i;
        }
    }
    return best;
}

static bool prime_is_distinct(const mpz_t prime, mpz_t *existing, size_t count) {
    for (size_t i = 0; i < count; ++i) {
        if (mpz_cmp(prime, existing[i]) == 0) {
            return false;
        }
    }
    return true;
}

static void ceil_nth_root(mpz_t out, const mpz_t value, unsigned long n) {
    mpz_t powered;
    mpz_init(powered);
    mpz_root(out, value, n);
    mpz_pow_ui(powered, out, n);
    if (mpz_cmp(powered, value) < 0) {
        mpz_add_ui(out, out, 1UL);
    }
    mpz_clear(powered);
}

static int decimal_digits_mpz(const mpz_t value) {
    int digits = 0;
    char *decimal = mpz_get_str(NULL, 10, value);
    digits = (int) strlen(decimal);
    free_gmp_string(decimal);
    return digits;
}

static int compute_min_constructible_digits(
    const family_spec_t *family,
    const int *factor_digits,
    mpz_t *pow10,
    unsigned long probable_prime_reps
) {
    mpz_t primes[MAX_FACTORS];
    mpz_t n;
    int digits = INT_MAX;

    for (size_t i = 0; i < family->factor_count; ++i) {
        mpz_init(primes[i]);
    }
    mpz_init(n);

    for (size_t i = 0; i < family->factor_count; ++i) {
        if (!generate_probable_prime_exact_digits(
                primes[i],
                factor_digits[i],
                pow10,
                primes,
                i,
                probable_prime_reps,
                0UL)) {
            goto cleanup;
        }
    }

    multiply_prime_powers(n, family, primes);
    digits = decimal_digits_mpz(n);

cleanup:
    for (size_t i = 0; i < family->factor_count; ++i) {
        mpz_clear(primes[i]);
    }
    mpz_clear(n);
    return digits;
}

static bool generate_probable_prime_in_range_distinct(
    mpz_t out,
    const mpz_t lower,
    const mpz_t upper,
    unsigned long probable_prime_reps,
    mpz_t *existing,
    size_t existing_count,
    unsigned long ordinal
) {
    mpz_t candidate;
    mpz_t cursor;
    unsigned long seen_count = 0UL;

    mpz_init(candidate);
    mpz_init(cursor);

    if (mpz_cmp(lower, upper) > 0) {
        mpz_clear(candidate);
        mpz_clear(cursor);
        return false;
    }

    mpz_set(cursor, lower);
    mpz_sub_ui(cursor, cursor, 1UL);
    while (true) {
        mpz_nextprime(candidate, cursor);
        if (mpz_cmp(candidate, upper) > 0) {
            break;
        }
        if (prime_is_distinct(candidate, existing, existing_count) &&
            mpz_probab_prime_p(candidate, (int) probable_prime_reps) > 0) {
            if (seen_count == ordinal) {
                mpz_set(out, candidate);
                mpz_clear(candidate);
                mpz_clear(cursor);
                return true;
            }
            seen_count += 1UL;
        }
        mpz_set(cursor, candidate);
    }

    mpz_clear(candidate);
    mpz_clear(cursor);
    return false;
}

static bool generate_probable_prime_exact_digits(
    mpz_t out,
    int digits,
    mpz_t *pow10,
    mpz_t *existing,
    size_t existing_count,
    unsigned long probable_prime_reps,
    unsigned long ordinal
) {
    mpz_t lower;
    mpz_t upper;
    bool ok = false;

    if (digits <= 0) {
        fatalf("invalid digit request: %d", digits);
    }

    mpz_init(lower);
    mpz_init(upper);
    if (digits == 1) {
        mpz_set_ui(lower, 2UL);
        mpz_set_ui(upper, 7UL);
    } else {
        mpz_set(lower, pow10[digits - 1]);
        mpz_set(upper, pow10[digits]);
        mpz_sub_ui(upper, upper, 1UL);
    }

    ok = generate_probable_prime_in_range_distinct(out, lower, upper, probable_prime_reps, existing, existing_count, ordinal);
    mpz_clear(lower);
    mpz_clear(upper);
    return ok;
}

static bool generate_probable_prime_in_range(
    mpz_t out,
    const mpz_t lower,
    const mpz_t upper,
    unsigned long probable_prime_reps,
    unsigned long ordinal
) {
    return generate_probable_prime_in_range_distinct(out, lower, upper, probable_prime_reps, NULL, 0U, ordinal);
}

static void multiply_prime_powers(mpz_t out, const family_spec_t *family, mpz_t *primes) {
    mpz_t factor_power;
    mpz_init(factor_power);
    mpz_set_ui(out, 1UL);

    for (size_t i = 0; i < family->factor_count; ++i) {
        mpz_pow_ui(factor_power, primes[i], family->exponents[i]);
        mpz_mul(out, out, factor_power);
    }

    mpz_clear(factor_power);
}

static void compute_sample_metrics(const family_spec_t *family, mpz_t n, int *factor_digits, sample_result_t *sample, mpfr_prec_t precision) {
    mpfr_t n_mpfr;
    mpfr_t n_log10;
    mpfr_t neg_log10;

    mpfr_init2(n_mpfr, precision);
    mpfr_init2(n_log10, precision);
    mpfr_init2(neg_log10, precision);

    sample->d_value = family->d_value;
    build_vector_text(family->exponents, family->factor_count, sample->exponent_vector, sizeof(sample->exponent_vector));
    build_int_vector_text(factor_digits, family->factor_count, sample->factor_digit_lengths, sizeof(sample->factor_digit_lengths));

    compute_number_features(n, sample->leading16, sample->trailing16, &sample->n_digits, &sample->n_bits);

    mpfr_set_z(n_mpfr, n, MPFR_RNDN);
    mpfr_log10(n_log10, n_mpfr, MPFR_RNDN);
    format_fixed_mpfr(n_log10, sample->n_log10, sizeof(sample->n_log10));

    if (family->d_value == 2UL) {
        mpfr_set_zero(neg_log10, 0);
    } else {
        mpfr_mul_ui(neg_log10, n_log10, family->d_value - 2UL, MPFR_RNDN);
        mpfr_div_ui(neg_log10, neg_log10, 2UL, MPFR_RNDN);
    }

    format_fixed_mpfr(neg_log10, sample->neg_log10_z, sizeof(sample->neg_log10_z));
    sample->neg_log10_value = mpfr_get_ld(neg_log10, MPFR_RNDN);
    format_z_scientific_from_neg(neg_log10, sample->z_sci, sizeof(sample->z_sci));
    snprintf(sample->status, sizeof(sample->status), "ok");

    mpfr_clear(n_mpfr);
    mpfr_clear(n_log10);
    mpfr_clear(neg_log10);
}

static bool generate_family_sample(
    const run_config_t *config,
    const family_spec_t *family,
    const family_support_t *support,
    int band_digits,
    mpz_t *pow10,
    sample_result_t *sample
) {
    int factor_digits[MAX_FACTORS] = {0};
    mpz_t primes[MAX_FACTORS];
    mpz_t n;

    for (size_t i = 0; i < family->factor_count; ++i) {
        mpz_init(primes[i]);
    }
    mpz_init(n);

    sample->band_digits = band_digits;
    sample->ok = false;

    if (family->factor_count == 1U) {
        mpz_t lower_bound;
        mpz_t upper_bound;
        mpz_t lower_root;
        mpz_t upper_root;
        int prime_digits = 0;
        unsigned long prime_bits = 0;
        char leading16[LEAD_TAIL_WIDTH + 1];
        char trailing16[LEAD_TAIL_WIDTH + 1];

        mpz_init(lower_bound);
        mpz_init(upper_bound);
        mpz_init(lower_root);
        mpz_init(upper_root);

        mpz_set(lower_bound, pow10[band_digits - 1]);
        mpz_sub_ui(upper_bound, pow10[band_digits], 1UL);
        ceil_nth_root(lower_root, lower_bound, family->exponents[0]);
        mpz_root(upper_root, upper_bound, family->exponents[0]);
        if (!generate_probable_prime_in_range(primes[0], lower_root, upper_root, config->probable_prime_reps, 0UL)) {
            mpz_clear(lower_bound);
            mpz_clear(upper_bound);
            mpz_clear(lower_root);
            mpz_clear(upper_root);
            for (size_t i = 0; i < family->factor_count; ++i) {
                mpz_clear(primes[i]);
            }
            mpz_clear(n);
            return false;
        }
        compute_number_features(primes[0], leading16, trailing16, &prime_digits, &prime_bits);
        factor_digits[0] = prime_digits;
        multiply_prime_powers(n, family, primes);
        compute_sample_metrics(family, n, factor_digits, sample, config->precision);
        sample->ok = sample->n_digits == band_digits;

        mpz_clear(lower_bound);
        mpz_clear(upper_bound);
        mpz_clear(lower_root);
        mpz_clear(upper_root);
    } else {
        mpz_t partial_product;
        mpz_t factor_power;
        mpz_t lower_bound;
        mpz_t upper_bound;
        mpz_t lower_last;
        mpz_t upper_last;
        size_t last_index = family->factor_count - 1U;

        if (family->exponents[last_index] != 1UL) {
            fatalf("multi-factor family %s must end with exponent 1 for exact balancing", family->name);
        }

        mpz_init(partial_product);
        mpz_init(factor_power);
        mpz_init(lower_bound);
        mpz_init(upper_bound);
        mpz_init(lower_last);
        mpz_init(upper_last);
        initialize_factor_targets(family, support, band_digits, factor_digits);
        while (compute_min_constructible_digits(family, factor_digits, pow10, config->probable_prime_reps) > band_digits) {
            size_t index = pick_adjustment_index(family, support, factor_digits, false);
            if (factor_digits[index] <= support->min_factor_digits[index]) {
                break;
            }
            factor_digits[index] -= 1;
        }

        {
            bool prefix_ok = true;
            mpz_set_ui(partial_product, 1UL);
            for (size_t i = 0; i < last_index; ++i) {
                if (!generate_probable_prime_exact_digits(
                        primes[i],
                        factor_digits[i],
                        pow10,
                        primes,
                        i,
                        config->probable_prime_reps,
                        0UL)) {
                    prefix_ok = false;
                    break;
                }
                mpz_pow_ui(factor_power, primes[i], family->exponents[i]);
                mpz_mul(partial_product, partial_product, factor_power);
            }

            if (prefix_ok) {
                mpz_set(lower_bound, pow10[band_digits - 1]);
                mpz_sub_ui(upper_bound, pow10[band_digits], 1UL);
                mpz_cdiv_q(lower_last, lower_bound, partial_product);
                mpz_fdiv_q(upper_last, upper_bound, partial_product);

                if (generate_probable_prime_in_range_distinct(
                        primes[last_index],
                        lower_last,
                        upper_last,
                        config->probable_prime_reps,
                        primes,
                        last_index,
                        0UL)) {
                    factor_digits[last_index] = decimal_digits_mpz(primes[last_index]);
                    multiply_prime_powers(n, family, primes);
                    compute_sample_metrics(family, n, factor_digits, sample, config->precision);
                    sample->ok = sample->n_digits == band_digits;
                }
            }
        }

        mpz_clear(partial_product);
        mpz_clear(factor_power);
        mpz_clear(lower_bound);
        mpz_clear(upper_bound);
        mpz_clear(lower_last);
        mpz_clear(upper_last);
    }

    for (size_t i = 0; i < family->factor_count; ++i) {
        mpz_clear(primes[i]);
    }
    mpz_clear(n);
    return sample->ok;
}

static void snapshot_spot_sample(sample_snapshot_t *slot, int band_digits, unsigned long sample_index, const char *leading16, const char *trailing16, const char *status) {
    slot->valid = true;
    slot->band_digits = band_digits;
    slot->sample_index = sample_index;
    snprintf(slot->leading16, sizeof(slot->leading16), "%s", leading16);
    snprintf(slot->trailing16, sizeof(slot->trailing16), "%s", trailing16);
    snprintf(slot->status, sizeof(slot->status), "%s", status);
}

static void generate_deterministic_exact_digits(mpz_t out, int digits, unsigned long sample_index, int band_digits, mpz_t *pow10) {
    if (digits == 1) {
        static const unsigned long odd_single_digits[] = {1UL, 3UL, 5UL, 7UL, 9UL};
        mpz_set_ui(out, odd_single_digits[(sample_index + (unsigned long) band_digits) % ARRAY_LEN(odd_single_digits)]);
        return;
    }

    mpz_set(out, pow10[digits - 1]);
    if (mpz_even_p(out)) {
        mpz_add_ui(out, out, 1UL);
    }
    mpz_add_ui(out, out, 2UL * (sample_index + (unsigned long) band_digits));
    if (mpz_cmp(out, pow10[digits]) >= 0) {
        mpz_sub(out, out, pow10[digits - 1]);
        if (mpz_even_p(out)) {
            mpz_add_ui(out, out, 1UL);
        }
        mpz_add(out, out, pow10[digits - 1]);
    }
}

static unsigned long sieve_primes(unsigned long limit, unsigned long **primes_out) {
    bool *flags = xmalloc((size_t) (limit + 1) * sizeof(bool));
    memset(flags, true, (size_t) (limit + 1) * sizeof(bool));
    flags[0] = false;
    flags[1] = false;
    for (unsigned long i = 2; i * i <= limit; ++i) {
        if (!flags[i]) {
            continue;
        }
        for (unsigned long j = i * i; j <= limit; j += i) {
            flags[j] = false;
        }
    }

    unsigned long count = 0;
    for (unsigned long i = 2; i <= limit; ++i) {
        if (flags[i]) {
            count += 1;
        }
    }

    unsigned long *primes = xmalloc(count * sizeof(unsigned long));
    unsigned long index = 0;
    for (unsigned long i = 2; i <= limit; ++i) {
        if (flags[i]) {
            primes[index++] = i;
        }
    }

    free(flags);
    *primes_out = primes;
    return count;
}

static void run_spot_check(const run_config_t *config, mpz_t *pow10) {
    FILE *samples_file;
    FILE *bands_file;
    FILE *summary_file;
    unsigned long *small_primes = NULL;
    unsigned long prime_count = sieve_primes(SPOT_CHECK_SMALL_FACTOR_BOUND, &small_primes);
    spot_summary_t summary;

    memset(&summary, 0, sizeof(summary));
    summary.first_factor_missing.valid = false;

    ensure_directory(config->out_dir);
    samples_file = open_output_file(config->out_dir, "spot_check_samples.csv");
    bands_file = open_output_file(config->out_dir, "spot_check_bands.csv");
    summary_file = open_output_file(config->out_dir, "spot_check_summary.md");

    write_spot_samples_header(samples_file);
    write_spot_bands_header(bands_file);
    write_spot_summary_stub(summary_file, config);
    fflush(summary_file);

    for (int band_digits = config->min_digits; band_digits <= config->max_digits; ++band_digits) {
        unsigned long factors_found = 0;
        unsigned long factor_missing = 0;
        unsigned long smallest_factor_found = 0;
        bool band_has_factor = false;

        for (unsigned long sample_index = 0; sample_index < config->samples_per_band; ++sample_index) {
            mpz_t n;
            mpfr_t n_mpfr;
            mpfr_t n_log10;
            char leading16[LEAD_TAIL_WIDTH + 1];
            char trailing16[LEAD_TAIL_WIDTH + 1];
            char n_log10_text[MAX_FIXED_TEXT];
            char status[MAX_STATUS_TEXT];
            int n_digits = 0;
            unsigned long n_bits = 0;
            unsigned long found_factor = 0;

            mpz_init(n);
            mpfr_init2(n_mpfr, config->precision);
            mpfr_init2(n_log10, config->precision);

            generate_deterministic_exact_digits(n, band_digits, sample_index, band_digits, pow10);
            compute_number_features(n, leading16, trailing16, &n_digits, &n_bits);
            mpfr_set_z(n_mpfr, n, MPFR_RNDN);
            mpfr_log10(n_log10, n_mpfr, MPFR_RNDN);
            format_fixed_mpfr(n_log10, n_log10_text, sizeof(n_log10_text));

            for (unsigned long i = 0; i < prime_count; ++i) {
                unsigned long p = small_primes[i];
                if (p == 2UL) {
                    continue;
                }
                if (mpz_divisible_ui_p(n, p) != 0) {
                    found_factor = p;
                    break;
                }
            }

            if (found_factor != 0UL) {
                snprintf(status, sizeof(status), "small_factor_found:%lu", found_factor);
                factors_found += 1;
                if (!band_has_factor || found_factor < smallest_factor_found) {
                    smallest_factor_found = found_factor;
                    band_has_factor = true;
                }
                if (!summary.has_smallest_factor || found_factor < summary.smallest_factor_found) {
                    summary.has_smallest_factor = true;
                    summary.smallest_factor_found = found_factor;
                    snapshot_spot_sample(&summary.first_factor_found, band_digits, sample_index, leading16, trailing16, status);
                }
            } else {
                snprintf(status, sizeof(status), "no_small_factor_found");
                factor_missing += 1;
                if (!summary.first_factor_missing.valid) {
                    snapshot_spot_sample(&summary.first_factor_missing, band_digits, sample_index, leading16, trailing16, status);
                }
            }

            fprintf(
                samples_file,
                "%d,%lu,%d,%lu,%s,%s,%s,%lu,%s\n",
                band_digits,
                sample_index,
                n_digits,
                n_bits,
                n_log10_text,
                leading16,
                trailing16,
                found_factor,
                status
            );

            summary.total_samples += 1;
            mpz_clear(n);
            mpfr_clear(n_mpfr);
            mpfr_clear(n_log10);
        }

        summary.factors_found += factors_found;
        summary.factor_missing += factor_missing;

        fprintf(
            bands_file,
            "%d,%lu,%lu,%lu,%lu,%lu,%s\n",
            band_digits,
            config->samples_per_band,
            config->samples_per_band,
            factors_found,
            factor_missing,
            band_has_factor ? smallest_factor_found : 0UL,
            "ok"
        );
    }

    rewind(summary_file);
    if (ftruncate(fileno(summary_file), 0) != 0) {
        fatalf("failed to rewrite spot-check summary: %s", strerror(errno));
    }
    write_spot_summary(summary_file, config, &summary);

    free(small_primes);
    fclose(samples_file);
    fclose(bands_file);
    fclose(summary_file);
}

static void run_main_study(const run_config_t *config, mpz_t *pow10) {
    FILE *samples_file;
    FILE *bands_file;
    FILE *summary_file;
    family_support_t support[ARRAY_LEN(FAMILY_SPECS)];
    summary_stats_t summary;

    build_all_support(support);
    init_summary(&summary);
    ensure_directory(config->out_dir);

    samples_file = open_output_file(config->out_dir, "samples.csv");
    bands_file = open_output_file(config->out_dir, "bands.csv");
    summary_file = open_output_file(config->out_dir, "summary.md");

    write_samples_header(samples_file);
    write_bands_header(bands_file);
    write_main_summary_stub(summary_file, config);
    fflush(summary_file);

    for (int band_digits = config->min_digits; band_digits <= config->max_digits; ++band_digits) {
        for (size_t family_index = 0; family_index < ARRAY_LEN(FAMILY_SPECS); ++family_index) {
            const family_spec_t *family = &FAMILY_SPECS[family_index];
            const family_support_t *family_support = &support[family_index];
            long double *neg_values = NULL;
            unsigned long unit_z_count = 0;
            unsigned long subunit_z_count = 0;
            unsigned long samples_built = 0;
            long double min_neg = 0.0L;
            long double median_neg = 0.0L;
            long double max_neg = 0.0L;

            summary.total_band_rows += 1;
            summary.total_samples_requested += config->samples_per_band;

            if (band_digits < family_support->min_digits) {
                summary.unsupported_band_rows += 1;
                write_band_row(
                    bands_file,
                    band_digits,
                    family,
                    false,
                    config->samples_per_band,
                    0UL,
                    0UL,
                    0UL,
                    0.0L,
                    0.0L,
                    0.0L,
                    "unsupported_small_band"
                );
                continue;
            }

            summary.supported_band_rows += 1;
            neg_values = xmalloc((size_t) config->samples_per_band * sizeof(long double));
            {
                sample_result_t sample;
                memset(&sample, 0, sizeof(sample));

                if (!generate_family_sample(config, family, family_support, band_digits, pow10, &sample)) {
                    free(neg_values);
                    fclose(samples_file);
                    fclose(bands_file);
                    fclose(summary_file);
                    fatalf("generation failed for family %s in band %d", family->name, band_digits);
                }

                min_neg = sample.neg_log10_value;
                max_neg = sample.neg_log10_value;
                unit_z_count = strcmp(sample.z_sci, "1") == 0 ? config->samples_per_band : 0UL;
                subunit_z_count = sample.neg_log10_value > 0.0L ? config->samples_per_band : 0UL;

                for (unsigned long sample_index = 0; sample_index < config->samples_per_band; ++sample_index) {
                    write_sample_row(samples_file, family, &sample, config, sample_index);
                    neg_values[samples_built] = sample.neg_log10_value;
                    summary.total_samples_built += 1;
                    summary_note_sample(&summary, &sample, family, sample_index);
                    samples_built += 1;
                }
            }

            median_neg = compute_median(neg_values, (size_t) samples_built);
            write_band_row(
                bands_file,
                band_digits,
                family,
                true,
                config->samples_per_band,
                samples_built,
                unit_z_count,
                subunit_z_count,
                min_neg,
                median_neg,
                max_neg,
                "ok"
            );
            free(neg_values);
        }
    }

    rewind(summary_file);
    if (ftruncate(fileno(summary_file), 0) != 0) {
        fatalf("failed to rewrite summary: %s", strerror(errno));
    }
    write_main_summary(summary_file, config, support, &summary);

    fclose(samples_file);
    fclose(bands_file);
    fclose(summary_file);
}

static bool parse_ulong_arg(const char *text, unsigned long *value_out) {
    char *end = NULL;
    errno = 0;
    unsigned long value = strtoul(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0') {
        return false;
    }
    *value_out = value;
    return true;
}

static void print_usage(FILE *stream) {
    fprintf(stream, "Usage:\n");
    fprintf(stream, "  z_bands [options]\n\n");

    fprintf(stream, "Default Run:\n");
    fprintf(stream, "  Digit bands:       %d..%d\n", DEFAULT_MIN_DIGITS, DEFAULT_MAX_DIGITS);
    fprintf(stream, "  Samples per pair:  %lu\n", DEFAULT_SAMPLES_PER_BAND);
    fprintf(stream, "  Output files:      samples.csv, bands.csv, summary.md\n\n");

    fprintf(stream, "Full Run:\n");
    fprintf(stream, "  z_bands --full\n");
    fprintf(stream, "  Digit bands:       %d..%d\n", DEFAULT_FULL_MIN_DIGITS, DEFAULT_FULL_MAX_DIGITS);
    fprintf(stream, "  Samples per pair:  %lu\n", DEFAULT_FULL_SAMPLES_PER_BAND);
    fprintf(stream, "  Constraint:        --full cannot be combined with --min-digits,\n");
    fprintf(stream, "                     --max-digits, or --samples-per-band\n\n");

    fprintf(stream, "Options:\n");
    fprintf(stream, "  --full                  Run the exhaustive full profile.\n");
    fprintf(stream, "  --min-digits N          Set the lower digit band for a custom run.\n");
    fprintf(stream, "  --max-digits N          Set the upper digit band for a custom run.\n");
    fprintf(stream, "  --samples-per-band N    Set sample rows per supported band-family pair.\n");
    fprintf(stream, "  --out-dir PATH          Write output files under PATH.\n");
    fprintf(stream, "  --spot-check-factor     Run bounded small-factor spot-check mode.\n");
    fprintf(stream, "  --check                 Run deterministic correctness checks and exit.\n");
    fprintf(stream, "  --help                  Show this help text.\n\n");

    fprintf(stream, "Examples (roughly increasing cost):\n");
    fprintf(stream, "  z_bands --check\n");
    fprintf(stream, "  z_bands\n");
    fprintf(stream, "  z_bands --min-digits 1 --max-digits 64 --samples-per-band 1\n");
    fprintf(stream, "  z_bands --min-digits 1 --max-digits 128 --samples-per-band 8\n");
    fprintf(stream, "  z_bands --full\n");
}

static void init_default_config(run_config_t *config) {
    config->min_digits = DEFAULT_MIN_DIGITS;
    config->max_digits = DEFAULT_MAX_DIGITS;
    config->samples_per_band = DEFAULT_SAMPLES_PER_BAND;
    config->out_dir = DEFAULT_OUT_DIR;
    config->probable_prime_reps = DEFAULT_PROBABLE_PRIME_REPS;
    config->precision = DEFAULT_PRECISION;
    config->spot_check_factor = false;
    config->check_mode = false;
}

static void parse_args(int argc, char **argv, run_config_t *config) {
    bool saw_full = false;
    bool saw_min_digits = false;
    bool saw_max_digits = false;
    bool saw_samples_per_band = false;

    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--min-digits") == 0) {
            unsigned long value = 0;
            if (i + 1 >= argc || !parse_ulong_arg(argv[++i], &value)) {
                fatalf("invalid value for --min-digits");
            }
            config->min_digits = (int) value;
            saw_min_digits = true;
        } else if (strcmp(argv[i], "--max-digits") == 0) {
            unsigned long value = 0;
            if (i + 1 >= argc || !parse_ulong_arg(argv[++i], &value)) {
                fatalf("invalid value for --max-digits");
            }
            config->max_digits = (int) value;
            saw_max_digits = true;
        } else if (strcmp(argv[i], "--samples-per-band") == 0) {
            unsigned long value = 0;
            if (i + 1 >= argc || !parse_ulong_arg(argv[++i], &value)) {
                fatalf("invalid value for --samples-per-band");
            }
            config->samples_per_band = value;
            saw_samples_per_band = true;
        } else if (strcmp(argv[i], "--full") == 0) {
            saw_full = true;
        } else if (strcmp(argv[i], "--seed") == 0) {
            fatalf("--seed is not supported; z_bands is fully deterministic");
        } else if (strcmp(argv[i], "--out-dir") == 0) {
            if (i + 1 >= argc) {
                fatalf("missing value for --out-dir");
            }
            config->out_dir = argv[++i];
        } else if (strcmp(argv[i], "--spot-check-factor") == 0) {
            config->spot_check_factor = true;
        } else if (strcmp(argv[i], "--check") == 0) {
            config->check_mode = true;
        } else if (strcmp(argv[i], "--help") == 0) {
            print_usage(stdout);
            exit(EXIT_SUCCESS);
        } else {
            print_usage(stderr);
            fatalf("unknown argument: %s", argv[i]);
        }
    }

    if (saw_full && (saw_min_digits || saw_max_digits || saw_samples_per_band)) {
        fatalf("--full cannot be combined with --min-digits, --max-digits, or --samples-per-band");
    }
    if (saw_full) {
        config->min_digits = DEFAULT_FULL_MIN_DIGITS;
        config->max_digits = DEFAULT_FULL_MAX_DIGITS;
        config->samples_per_band = DEFAULT_FULL_SAMPLES_PER_BAND;
    }
    if (config->min_digits < 1 || config->max_digits < config->min_digits) {
        fatalf("invalid digit band range");
    }
    if (config->samples_per_band == 0UL) {
        fatalf("--samples-per-band must be positive");
    }
}

static bool approx_equal(long double lhs, long double rhs, long double tolerance) {
    long double diff = lhs - rhs;
    if (diff < 0.0L) {
        diff = -diff;
    }
    return diff <= tolerance;
}

static void direct_sample_for_check(unsigned long n_value, unsigned long d_value, mpfr_prec_t precision, char *z_out, size_t z_out_size, long double *neg_out) {
    mpz_t n;
    mpfr_t n_mpfr;
    mpfr_t n_log10;
    mpfr_t neg_log10;

    mpz_init_set_ui(n, n_value);
    mpfr_init2(n_mpfr, precision);
    mpfr_init2(n_log10, precision);
    mpfr_init2(neg_log10, precision);

    mpfr_set_z(n_mpfr, n, MPFR_RNDN);
    mpfr_log10(n_log10, n_mpfr, MPFR_RNDN);
    if (d_value == 2UL) {
        mpfr_set_zero(neg_log10, 0);
    } else {
        mpfr_mul_ui(neg_log10, n_log10, d_value - 2UL, MPFR_RNDN);
        mpfr_div_ui(neg_log10, neg_log10, 2UL, MPFR_RNDN);
    }

    format_z_scientific_from_neg(neg_log10, z_out, z_out_size);
    *neg_out = mpfr_get_ld(neg_log10, MPFR_RNDN);

    mpz_clear(n);
    mpfr_clear(n_mpfr);
    mpfr_clear(n_log10);
    mpfr_clear(neg_log10);
}

static int run_checks(void) {
    int failures = 0;
    mpz_t *pow10 = NULL;
    family_support_t support[ARRAY_LEN(FAMILY_SPECS)];
    build_all_support(support);
    init_pow10_table(&pow10, 32);

    struct {
        unsigned long n;
        unsigned long d;
        long double z;
    } cases[] = {
        {2UL, 2UL, 1.0L},
        {3UL, 2UL, 1.0L},
        {4UL, 3UL, 0.5L},
        {5UL, 2UL, 1.0L},
        {6UL, 4UL, 1.0L / 6.0L},
        {9UL, 3UL, 1.0L / 3.0L},
        {25UL, 3UL, 0.2L},
    };

    fprintf(stdout, "z_bands check: arithmetic regressions\n");
    for (size_t i = 0; i < ARRAY_LEN(cases); ++i) {
        char z_text[MAX_SCI_TEXT];
        long double neg = 0.0L;
        long double actual_z = 0.0L;

        direct_sample_for_check(cases[i].n, cases[i].d, DEFAULT_PRECISION, z_text, sizeof(z_text), &neg);
        actual_z = strcmp(z_text, "1") == 0 ? 1.0L : strtold(z_text, NULL);
        if (!approx_equal(actual_z, cases[i].z, 1.0e-12L)) {
            fprintf(stdout, "  FAIL n=%lu expected %.18Lf got %s\n", cases[i].n, cases[i].z, z_text);
            failures += 1;
        } else {
            fprintf(stdout, "  PASS n=%lu z=%s\n", cases[i].n, z_text);
        }
        (void) neg;
    }

    fprintf(stdout, "z_bands check: family constructors\n");
    for (size_t family_index = 0; family_index < ARRAY_LEN(FAMILY_SPECS); ++family_index) {
        run_config_t config;
        sample_result_t sample;
        int band_digits = support[family_index].min_digits;

        init_default_config(&config);
        config.precision = DEFAULT_PRECISION;
        config.samples_per_band = 1;
        memset(&sample, 0, sizeof(sample));

        if (!generate_family_sample(&config, &FAMILY_SPECS[family_index], &support[family_index], band_digits, pow10, &sample)) {
            fprintf(stdout, "  FAIL family=%s generation failed\n", FAMILY_SPECS[family_index].name);
            failures += 1;
        } else if (sample.n_digits != band_digits || sample.d_value != FAMILY_SPECS[family_index].d_value) {
            fprintf(stdout, "  FAIL family=%s digits=%d d=%lu\n", FAMILY_SPECS[family_index].name, sample.n_digits, sample.d_value);
            failures += 1;
        } else if (strcmp(FAMILY_SPECS[family_index].name, "probable_prime") == 0 && strcmp(sample.z_sci, "1") != 0) {
            fprintf(stdout, "  FAIL family=%s expected fixed point got %s\n", FAMILY_SPECS[family_index].name, sample.z_sci);
            failures += 1;
        } else if (strcmp(FAMILY_SPECS[family_index].name, "probable_prime") != 0 && !(sample.neg_log10_value > 0.0L)) {
            fprintf(stdout, "  FAIL family=%s expected strict contraction got %s\n", FAMILY_SPECS[family_index].name, sample.neg_log10_z);
            failures += 1;
        } else {
            fprintf(stdout, "  PASS family=%s band=%d z=%s\n", FAMILY_SPECS[family_index].name, band_digits, sample.z_sci);
        }

    }

    clear_pow10_table(pow10, 32);
    if (failures != 0) {
        fprintf(stdout, "z_bands check: %d failure(s)\n", failures);
        return EXIT_FAILURE;
    }
    fprintf(stdout, "z_bands check: all checks passed\n");
    return EXIT_SUCCESS;
}

int main(int argc, char **argv) {
    run_config_t config;
    mpz_t *pow10 = NULL;

    init_default_config(&config);
    parse_args(argc, argv, &config);

    if (config.check_mode) {
        return run_checks();
    }

    init_pow10_table(&pow10, config.max_digits);
    if (config.spot_check_factor) {
        run_spot_check(&config, pow10);
    } else {
        run_main_study(&config, pow10);
    }
    clear_pow10_table(pow10, config.max_digits);
    return EXIT_SUCCESS;
}
