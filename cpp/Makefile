CXX := c++
CXXFLAGS := -std=c++17 -Wall -Wextra -Wpedantic -O2

TARGET := receiver_model
SOURCE := receiver_model.cpp

INPUT := ../vectors/input_samples.csv
OUTPUT := ../vectors/cpp_expected.csv

.PHONY: all run clean

all: $(TARGET)

$(TARGET): $(SOURCE)
	$(CXX) $(CXXFLAGS) $(SOURCE) -o $(TARGET)

run: $(TARGET)
	./$(TARGET) $(INPUT) $(OUTPUT)

clean:
	rm -f $(TARGET) $(OUTPUT)
