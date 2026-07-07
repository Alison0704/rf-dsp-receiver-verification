#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

struct InputSample {
    int32_t sample_index;
    int16_t i_in;
    int16_t q_in;
};

struct OutputSample {
    int32_t sample_index;
    int16_t i_in;
    int16_t q_in;
    uint8_t output_valid;
    int32_t fir_acc_i;
    int32_t fir_acc_q;
    int16_t fir_i;
    int16_t fir_q;
    uint8_t bit_msb;
    uint8_t bit_lsb;
};

std::vector<InputSample> read_input_csv(
    const std::filesystem::path& input_path
) {
    std::ifstream input_file(input_path);

    if (!input_file.is_open()) {
        throw std::runtime_error(
            "Could not open input file: " + input_path.string()
        );
    }

    std::string line;

    // Skip the CSV header.
    if (!std::getline(input_file, line)) {
        throw std::runtime_error("Input CSV is empty.");
    }

    std::vector<InputSample> samples;

    while (std::getline(input_file, line)) {
        if (line.empty()) {
            continue;
        }

        std::stringstream parser(line);
        std::string field;

        InputSample sample{};

        std::getline(parser, field, ',');
        sample.sample_index = std::stoi(field);

        std::getline(parser, field, ',');
        sample.i_in = static_cast<int16_t>(std::stoi(field));

        std::getline(parser, field, ',');
        sample.q_in = static_cast<int16_t>(std::stoi(field));

        samples.push_back(sample);
    }

    if (samples.empty()) {
        throw std::runtime_error(
            "Input CSV contains no samples."
        );
    }

    return samples;
}

std::vector<OutputSample> run_receiver(
    const std::vector<InputSample>& inputs
) {
    constexpr std::array<int32_t, 5> coefficients{
        1, 2, 3, 2, 1
    };

    constexpr int32_t normalization = 9;

    std::array<int32_t, 5> delay_i{};
    std::array<int32_t, 5> delay_q{};

    std::vector<OutputSample> outputs;
    outputs.reserve(inputs.size());

    for (std::size_t sample_number = 0;
         sample_number < inputs.size();
         ++sample_number) {

        // Shift the existing samples through the delay line.
        for (std::size_t tap = delay_i.size() - 1;
             tap > 0;
             --tap) {
            delay_i[tap] = delay_i[tap - 1];
            delay_q[tap] = delay_q[tap - 1];
        }

        delay_i[0] = inputs[sample_number].i_in;
        delay_q[0] = inputs[sample_number].q_in;

        int32_t accumulator_i = 0;
        int32_t accumulator_q = 0;

        for (std::size_t tap = 0;
             tap < coefficients.size();
             ++tap) {
            accumulator_i += delay_i[tap] * coefficients[tap];
            accumulator_q += delay_q[tap] * coefficients[tap];
        }

        OutputSample output{};

        output.sample_index =
            inputs[sample_number].sample_index;

        output.i_in = inputs[sample_number].i_in;
        output.q_in = inputs[sample_number].q_in;

        output.fir_acc_i = accumulator_i;
        output.fir_acc_q = accumulator_q;

        // Five accepted inputs are required before the FIR output
        // is considered fully valid.
        if (sample_number >= coefficients.size() - 1) {
            output.output_valid = 1;

            // Signed C++ integer division truncates toward zero.
            output.fir_i = static_cast<int16_t>(
                accumulator_i / normalization
            );

            output.fir_q = static_cast<int16_t>(
                accumulator_q / normalization
            );

            // QPSK hard decisions:
            // Q sign determines the MSB.
            // I sign determines the LSB.
            // Zero is treated as positive.
            output.bit_msb =
                static_cast<uint8_t>(output.fir_q < 0);

            output.bit_lsb =
                static_cast<uint8_t>(output.fir_i < 0);
        }

        outputs.push_back(output);
    }

    return outputs;
}

void write_output_csv(
    const std::filesystem::path& output_path,
    const std::vector<OutputSample>& outputs
) {
    if (output_path.has_parent_path()) {
        std::filesystem::create_directories(
            output_path.parent_path()
        );
    }

    std::ofstream output_file(output_path);

    if (!output_file.is_open()) {
        throw std::runtime_error(
            "Could not create output file: "
            + output_path.string()
        );
    }

    output_file
        << "sample_index,"
        << "i_in,"
        << "q_in,"
        << "output_valid,"
        << "fir_acc_i,"
        << "fir_acc_q,"
        << "fir_i,"
        << "fir_q,"
        << "bit_msb,"
        << "bit_lsb\n";

    for (const OutputSample& output : outputs) {
        output_file
            << output.sample_index << ','
            << output.i_in << ','
            << output.q_in << ','
            << static_cast<int>(output.output_valid) << ','
            << output.fir_acc_i << ','
            << output.fir_acc_q << ','
            << output.fir_i << ','
            << output.fir_q << ','
            << static_cast<int>(output.bit_msb) << ','
            << static_cast<int>(output.bit_lsb)
            << '\n';
    }
}

int main(int argc, char* argv[]) {
    try {
        const std::filesystem::path input_path =
            argc >= 2
                ? argv[1]
                : "../vectors/input_samples.csv";

        const std::filesystem::path output_path =
            argc >= 3
                ? argv[2]
                : "../vectors/cpp_expected.csv";

        const std::vector<InputSample> inputs =
            read_input_csv(input_path);

        const std::vector<OutputSample> outputs =
            run_receiver(inputs);

        write_output_csv(output_path, outputs);

        std::size_t valid_outputs = 0;

        for (const OutputSample& output : outputs) {
            if (output.output_valid != 0) {
                ++valid_outputs;
            }
        }

        std::cout
            << "C++ receiver model completed.\n"
            << "Input samples: " << inputs.size() << '\n'
            << "Valid outputs: " << valid_outputs << '\n'
            << "Output file: " << output_path << '\n';

        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "Error: " << error.what() << '\n';

        return 1;
    }
}
