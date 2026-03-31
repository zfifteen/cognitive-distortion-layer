UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)
PKG_OK := $(shell pkg-config --exists gmp mpfr && echo yes || echo no)

ifeq ($(UNAME_S),Darwin)
else
$(error z_bands is Apple-Silicon-only and requires Darwin)
endif

ifeq ($(UNAME_M),arm64)
else
$(error z_bands is Apple-Silicon-only and requires arm64)
endif

ifeq ($(PKG_OK),yes)
else
$(error z_bands requires pkg-config packages for gmp and mpfr)
endif

CC := cc
CFLAGS := -std=c99 -O2 -Wall -Wextra -Wpedantic
CPPFLAGS := $(shell pkg-config --cflags gmp mpfr)
LDFLAGS := $(shell pkg-config --libs gmp mpfr)

REPO_ROOT := $(abspath ../../..)
BUILD_DIR := build
BIN := $(BUILD_DIR)/z_bands
SRC := z_bands.c
ARTIFACT_DIR := $(REPO_ROOT)/artifacts/reports/z_bands

.PHONY: all z-bands-smoke z-bands-full z-bands-check z-bands-clean

all: $(BIN)

$(BIN): $(SRC)
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) $(CPPFLAGS) $(SRC) $(LDFLAGS) -o $(BIN)

z-bands-smoke: $(BIN)
	$(BIN) --min-digits 1 --max-digits 32 --samples-per-band 4 --out-dir $(ARTIFACT_DIR)/smoke

z-bands-full: $(BIN)
	$(BIN) --min-digits 1 --max-digits 1234 --full --out-dir $(ARTIFACT_DIR)/full

z-bands-check: $(BIN)
	$(BIN) --check

z-bands-clean:
	rm -rf $(BUILD_DIR) $(ARTIFACT_DIR)
