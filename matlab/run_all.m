%% run_all.m

clearvars;
clc;
close all;

fprintf('RF/DSP Receiver MATLAB Reference\n');
fprintf('================================\n\n');

generate_vectors;

results = receiver_reference();

valid_results = results(results.output_valid == 1, :);

fprintf('\nValid receiver outputs\n');
fprintf('----------------------\n');

disp(valid_results);

fprintf('Reference-model execution complete.\n');
fprintf('Generated valid outputs: %d\n', height(valid_results));