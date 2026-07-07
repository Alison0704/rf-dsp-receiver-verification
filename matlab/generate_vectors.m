%% generate_vectors.m
% Generate shared signed I/Q test vectors for MATLAB, C++, and RTL.

clearvars;
clc;

rng(2026, "twister");

num_samples = 32;

i_samples = zeros(num_samples, 1, "int16");
q_samples = zeros(num_samples, 1, "int16");

%% Directed quadrant and boundary samples

i_samples(1:16) = int16([
     1000
    -1000
    -1000
     1000
        0
    -1000
        0
     1000
     2000
    -2000
    -2000
     2000
     1500
    -1500
     1500
    -1500
]);

q_samples(1:16) = int16([
     1000
     1000
    -1000
    -1000
     1000
        0
    -1000
        0
     2000
     2000
    -2000
    -2000
    -1500
     1500
     1500
    -1500
]);

%% Impulse-like and step-like samples

i_samples(17:24) = int16([
    3000
       0
       0
       0
       0
    2500
    2500
    2500
]);

q_samples(17:24) = int16([
       0
    3000
       0
       0
       0
   -2500
   -2500
   -2500
]);

%% Reproducible randomized samples

levels = int16([
    -3000
    -2000
    -1000
        0
     1000
     2000
     3000
]);

for sample = 25:num_samples
    while true
        i_candidate = levels(randi(numel(levels)));
        q_candidate = levels(randi(numel(levels)));

        if ~(i_candidate == 0 && q_candidate == 0)
            break;
        end
    end

    i_samples(sample) = i_candidate;
    q_samples(sample) = q_candidate;
end

%% Export the shared input file

sample_index = int32((0:num_samples - 1).');

input_table = table( ...
    sample_index, ...
    i_samples, ...
    q_samples, ...
    'VariableNames', {'sample_index', 'i_in', 'q_in'} ...
);

writetable(input_table, "input_samples.csv");

fprintf("Generated input_samples.csv\n");
fprintf("Number of samples: %d\n\n", num_samples);

disp(input_table);