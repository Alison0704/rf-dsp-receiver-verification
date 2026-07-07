function results = receiver_reference( ...
    input_filename, ...
    expected_filename, ...
    mat_filename ...
)
%RECEIVER_REFERENCE Fixed-point QPSK receiver golden model.
%
% Pipeline:
%   signed I/Q inputs
%   -> 5-tap FIR filter
%   -> integer division by 9
%   -> QPSK hard-decision demapper
%
% FIR coefficients:
%   [1, 2, 3, 2, 1] / 9
%
% Demapper:
%   I >= 0, Q >= 0 -> 00
%   I <  0, Q >= 0 -> 01
%   I <  0, Q <  0 -> 11
%   I >= 0, Q <  0 -> 10

    if nargin < 1
        input_filename = "input_samples.csv";
    end

    if nargin < 2
        expected_filename = "matlab_expected.csv";
    end

    if nargin < 3
        mat_filename = "receiver_results.mat";
    end

    %% Receiver configuration

    fir_coefficients = int32([1, 2, 3, 2, 1]);
    normalization = int32(9);
    num_taps = numel(fir_coefficients);

    %% Read and validate inputs

    input_table = readtable(input_filename);

    required_columns = {'sample_index', 'i_in', 'q_in'};
    
    missing_columns = setdiff( ...
        required_columns, ...
        input_table.Properties.VariableNames ...
    );

    if ~isempty(missing_columns)
        error( ...
            'Input file is missing columns: %s', ...
            strjoin(missing_columns, ', ') ...
        );
    end

    if isempty(input_table)
        error("Input test-vector file is empty.");
    end

    if any(input_table.i_in < intmin("int16")) || ...
       any(input_table.i_in > intmax("int16"))
        error("I input exceeds the signed 16-bit range.");
    end

    if any(input_table.q_in < intmin("int16")) || ...
       any(input_table.q_in > intmax("int16"))
        error("Q input exceeds the signed 16-bit range.");
    end

    sample_index = int32(input_table.sample_index);
    input_i = int16(input_table.i_in);
    input_q = int16(input_table.q_in);

    num_samples = height(input_table);

    %% Allocate receiver outputs

    output_valid = zeros(num_samples, 1, "uint8");

    fir_acc_i = zeros(num_samples, 1, "int32");
    fir_acc_q = zeros(num_samples, 1, "int32");

    fir_i = zeros(num_samples, 1, "int16");
    fir_q = zeros(num_samples, 1, "int16");

    bit_msb = zeros(num_samples, 1, "uint8");
    bit_lsb = zeros(num_samples, 1, "uint8");

    delay_i = zeros(1, num_taps, "int32");
    delay_q = zeros(1, num_taps, "int32");

    %% Process every accepted input sample

    for sample = 1:num_samples
        % Shift previous samples through the FIR delay line.
        delay_i(2:end) = delay_i(1:end - 1);
        delay_q(2:end) = delay_q(1:end - 1);

        delay_i(1) = int32(input_i(sample));
        delay_q(1) = int32(input_q(sample));

        accumulator_i = int32(0);
        accumulator_q = int32(0);

        for tap = 1:num_taps
            accumulator_i = accumulator_i + ...
                delay_i(tap) * fir_coefficients(tap);

            accumulator_q = accumulator_q + ...
                delay_q(tap) * fir_coefficients(tap);
        end

        fir_acc_i(sample) = accumulator_i;
        fir_acc_q(sample) = accumulator_q;

        % The first fully valid FIR result appears after five samples.
        if sample >= num_taps
            output_valid(sample) = uint8(1);

            % idivide(..., "fix") truncates toward zero.
            filtered_i = idivide( ...
                accumulator_i, ...
                normalization, ...
                "fix" ...
            );

            filtered_q = idivide( ...
                accumulator_q, ...
                normalization, ...
                "fix" ...
            );

            fir_i(sample) = int16(filtered_i);
            fir_q(sample) = int16(filtered_q);

            % QPSK hard decisions.
            %
            % bit_msb is determined by the sign of Q.
            % bit_lsb is determined by the sign of I.
            %
            % Zero is treated as positive.
            bit_msb(sample) = uint8(filtered_q < 0);
            bit_lsb(sample) = uint8(filtered_i < 0);
        end
    end

    %% Build and export the golden-reference table

    results = table(sample_index, input_i, input_q, output_valid, fir_acc_i, fir_acc_q, fir_i, fir_q, bit_msb, bit_lsb, 'VariableNames', {'sample_index', 'i_in', 'q_in', 'output_valid', 'fir_acc_i', 'fir_acc_q', 'fir_i', 'fir_q', 'bit_msb', 'bit_lsb'});

    writetable(results, expected_filename);

    metadata = struct();
    metadata.fir_coefficients = fir_coefficients;
    metadata.normalization = normalization;
    metadata.input_width_bits = 16;
    metadata.accumulator_width_bits = 32;
    metadata.rounding_policy = "truncate_toward_zero";
    metadata.zero_sign_policy = "zero_is_positive";
    metadata.num_samples = num_samples;
    metadata.num_valid_outputs = sum(output_valid);

    save(mat_filename, 'input_table', 'results', 'metadata');

    %% Sanity checks

    assert( ...
        all(output_valid(1:num_taps - 1) == 0), ...
        "The first four FIR outputs must be invalid." ...
    );

    assert( ...
        all(output_valid(num_taps:end) == 1), ...
        "All outputs after the FIR fills must be valid." ...
    );

    assert( ...
        all(ismember(bit_msb, uint8([0, 1]))), ...
        "Invalid MSB demapper output." ...
    );

    assert( ...
        all(ismember(bit_lsb, uint8([0, 1]))), ...
        "Invalid LSB demapper output." ...
    );

    fprintf("Generated %s\n", expected_filename);
    fprintf("Generated %s\n", mat_filename);
    fprintf("Input samples: %d\n", num_samples);
    fprintf("Valid FIR outputs: %d\n", sum(output_valid));
end