'''
Created on Jun 6, 2013

@author: dusenberrymw
'''
import math
from multiprocessing import Process, Queue, cpu_count


class Backpropagation(object):
    """Class for the Backpropagation type of training"""
    def __init__(self, learning_rate, momentum_coef):
        """ Constructor

        Learning rate = degree to which the parameters (weight and threshold
            values) will be changed during each iteration of training
        Momentum = degree to which the previous learning will affect this
            iteration's weight and threshold values. Effectively, it keeps
            the weight values from oscillating during training

        """
        self.learning_rate = learning_rate
        self.momentum_coef = momentum_coef

    def train(self, network, training_examples, iterations, unsupervised=False):
        """This trains the given network using the given example vectors
        of input data (index 1 for each example) against the associated
        target output(s) (index 0 for each example)

        Essentially look forward to determine error, then look backward to
            change weights and threshold values (which are currently stored
            on the current node) on connections from nodes in previous
            (backwards) layer

        Start with the output layer and find the (lowercase) delta (partial
            deriv of the cost function, J, with respect to the node's input),
            and the gradient (partial deriv of the cost function, J, with
            respect to one of the weights on the incoming inputs) for each
            output neuron.
        Then, for each neuron in the hidden layer(s), find the delta and
            gradient.
        Then, update each neuron's weights and threshold value by subtracting
            gradient multiplied by the learning rate, alpha.  Subtract because
            the gradient (and delta values since they are both partial derivs)
            will give direction of gradient AScent, and we want to move in the
            opposite direction in order to lower the overall error (minimize
            the cost function, J).

        """
        if unsupervised:
            # For now this means we are training a sparse autoencoder.
            #    Therefore, we need to keep a running estimate of the
            #    "sparsity" of a node, where we try to keep the activation
            #    of the node stay close to a small value near 0 known as
            #    rho (Greek lower case p) or the 'sparsity parameter',
            #    which we will set to 0.05.
            # This forces the network to learn the smallest set of features
            #    necessary to accurately build a close estimate of the original
            #    input vector
            # In this case, we set the input vector equal to the target vector,
            #    and usually set a smaller value for the number of hidden nodes
            # Then perform normal backpropagation, and during that, for each
            #    hidden node, also update the rho_estimate, and then update the
            #    threshold value
            rho = 0.05
            rho_estimates = [0] * len(network.layers[0].neurons) # set to 0 for each node
            beta = 0.2 # the learning rate for updating the threshold terms
        for iteration_counter in range(iterations):
            # for each row of data
            for training_example in training_examples:
                target_output_vector = training_example[0]
                input_vector = training_example[1]
                # prime the network on this row of input data
                #    -this will cause local_output (activation) values to be
                #     set for each neuron
                network.compute_network_output(input_vector)

                # Note: next_layer_deltas is a vector of the single
                #    delta values for each node in the next
                #    (forward) layer
                next_layer_deltas = []
                next_layer_weights = []
                isOutputLayer = True
                for layer in reversed(network.layers): # iterate backwards
                    derivative = layer.activation_function.derivative
                    this_layer_deltas = [] # values from current layer
                    this_layer_weights = []
                    for j, neuron in enumerate(layer.neurons):
                        # The output layer neurons are treated slightly
                        #    different than the hidden neurons
                        if isOutputLayer:
                            if layer.activation_function.name == "Logistic":
                                # derivative simplifies down to just
                                #    subtracting the target from the
                                #    hypothesis
                                delta = neuron.local_output - target_output_vector[j]
                            else: # Tanh or Linear
                                delta = (neuron.local_output-target_output_vector[j])*derivative(neuron.local_output)
                        else: # for the hidden layer neurons
                            # Need to sum the products of the delta of
                            #    a neuron in the next (forward) layer and the
                            #    weight associated with the connection between
                            #    this hidden layer neuron and that neuron.
                            # This will basically determine how much this
                            #    neuron contributed to the error of the neuron
                            #    it is connected to
                            # Note: next_layer_deltas is a vector of the single
                            #    delta values for each node in the next
                            #    (forward) layer
                            sum_value = 0.0
                            for next_delta, weights in zip(next_layer_deltas,
                                                         next_layer_weights):
                                sum_value +=  weights[j] * next_delta
                            delta = (derivative(neuron.local_output) *
                                              sum_value)
                        # now store the delta and the list of weights
                        #    for this neuron into these storage lists for the
                        #    whole layer
                        this_layer_deltas.append(delta)
                        this_layer_weights.append(neuron.weights)
                        # Now, compute the gradient (partial deriv of cost
                        #    func, J, w/ respect to parameter ij) for each
                        #    weight_ij (parameter_ij) associated with
                        #    this neuron
                        for ij, input_ij in enumerate(neuron.inputs):
                            # compute gradient (partial deriv of cost J w/
                            #    respect to parameter ij)
                            # Note: index ij means from a previous
                            #    layer node i to this layer node j
                            # Note: Subtract in order to minimize error, since
                            #    partial derivs point in direction of gradient
                            #    AScent
                            # Then Gradient Descent: multiply by the learning
                            #    rate, and subtract from the current value
                            gradient_ij = delta * input_ij
                            neuron.weights[ij] -= self.learning_rate * gradient_ij
                        # Now, compute the gradient (partial deriv of cost
                        #    func, J, with respect to parameter ij) for the
                        #    threshold value (parameter_0j), by using a "1" as
                        #    the threshold "input value"
                        # -Note: index 0j means from a previous
                        #    layer threshold node 0 (threshold always has
                        #    index i=0) to this layer node j
                        #        -can also think of it as the threshold being
                        #            internal to this neuron
                        gradient_0j = delta * 1
                        neuron.threshold -= self.learning_rate * gradient_0j
                        if unsupervised and not isOutputLayer:
                            rho_estimates[j] = (0.999*rho_estimates[j] +
                                                0.001*neuron.local_output)
                            neuron.threshold -= (self.learning_rate * beta *
                                                 (rho_estimates[j] - rho))
                    # Once this layer is done, store the gradients and weights
                    #    from the current layer for the next layer iteration
                    #    (moving backwards)
                    next_layer_deltas = this_layer_deltas
                    next_layer_weights = this_layer_weights
                    isOutputLayer = False
        # Note: this is after the while loop
        self.iterations = iteration_counter


class LogisticActivationFunction(object):
    """The Logistic (Sigmoid) activation function, which is one of the
        possibilities that can be used by the network

    """
    def __init__(self):
        self.name = "Logistic"

    def activate(self, input_value):
        """Run the input value through the sigmoid function
        This will only return values between 0 and 1
        """
        try:
            return 1.0 / (1 + math.exp(-1.0*input_value))
        except OverflowError:
            # bound the numbers if there is an overflow
            if input_value < 0:
                return 0.0000000000001  #logistic function goes to 0 for small x
            else:
                return 0.9999999999999

    def derivative(self, fx):
        """Some training will require the derivative of the Logistic function

        Given F is the logistic (sigmoid) function, the derivative
            F'(x) = F(x) * (1 - F(x))

        F(x) will be passed in
        """
        return fx*(1.0-fx) # can add 0.1 to fix flat spot

    def inverse(self, input_value):
        """This will produce the inverse of the sigmoid function, which is
        useful in determining the original value before activation
        """
        return math.log(input_value/(1-input_value))

    def cost(self, hypothesis_output, target_output):
        """Cost function of a node using the Logistic activation function

        cost_theta(h_theta(x), y) = -log(h_theta(x))   if y = 1
                                    -log(1-h_theta(x)) if y = 0
                where h_theta(x) is the hypothesis (computed output) of the
                    node evaluated with respect to theta (parameter/weight)
                    evaluated at input x,
                and cost_theta is the "error" of the node with respect to
                    theta (parameter/weight) evaluated at the hypothesis of x
                    given the target value y

        This cost function essentially allows for no error if the hypothesis
            is equal to the target y, and high error otherwise

        """
        y = target_output
        h_x = hypothesis_output
        return -y*math.log(h_x)-(1-y)*math.log(1-h_x)


class TanhActivationFunction(object):
    """The Tanh (Logistic spinoff) activation function, which is one of the
        possibilities that can be used by the network

    """
    def __init__(self):
        self.name = "Tanh"

    def activate(self, input_value):
        """Run the input value through the tanh function"""
#         return math.tanh(input_value)
        return ((math.exp(input_value)-math.exp(-input_value)) /
               (math.exp(input_value)+math.exp(-input_value)))

    def derivative(self, fx):
        """Some training will require the derivative of the tanh function"""
        return (1.0-fx) * (1.0+fx) # can add 0.1 to fix flat spot

    def inverse(self, input_value):
        """This will produce the inverse of the tanh function, which is
        useful in determining the original value before activation
        """
        return math.atanh(input_value)

    def cost(self, hypothesis_output, target_output):
        """Cost function of a node using the Tanh activation function

        cost_theta(h_theta(x), y) = (1/2)*(|h_theta(x)-y|^2)

        """
        y = target_output
        h_x = hypothesis_output
        return (1/2)*(math.fabs(h_x-y)**2)


class LinearActivationFunction(object):
    """The Linear activation function, which is one of the
        possibilities that can be used by the network

    """
    def __init__(self):
        self.name = "Linear"

    def activate(self, input_value):
        """In the linear function, f(z) = z"""
        return input_value

    def derivative(self, fx):
        """Some training will require the derivative of the linear function
        which is just 1
        """
        return 1

    def inverse(self, input_value):
        """This will produce the inverse of the linear function, which is
        useful in determining the original value before activation
        """
        return input_value

    def cost(self, hypothesis_output, target_output):
        """Cost function of a node using the Linear activation function

        cost_theta(h_theta(x), y) = (1/2)*((h_theta(x)-y)^2)

        """
        y = target_output
        h_x = hypothesis_output
        return (1/2)*((h_x-y)**2)


def parallel_train(network, trainer, training_examples, iterations,
                   unsupervised=False, num_processes=None):
    """Train the given network using the given trainer in parallel using
    multiple processes.

    This will ultimately change the weights in the given network

    """
    if num_processes is None:
        # Determine the number of processes
        num_processes = cpu_count()
    if num_processes > len(training_examples):
        # there is not enough training examples to split amongst the entire
        #    possible number of processes, so reduce the number of processes
        #    used
        num_processes = len(training_examples)

    # Create the return queue to store the training networks that are returned
    #    from each process
    results_queue = Queue() # this is the multiprocessing queue

    # Train the training networks on a subset of the data
    #    -this is where the parallelization will occur
    #    -To get the training data subset for each process:
    #        -chunk the examples up into the correct number for the
    #            number of processes, and take each chunk
    #    -Note: when this process is created, a copy of any object that is
    #        accessed will be made, so no need to make a copy of the given
    #        network first
    chunk_amount = int(len(training_examples)/num_processes)
    jobs = [Process(target=_parallel_train_worker,
                    args=(network, trainer,
                          training_examples[process_num*chunk_amount:
                                            (process_num*chunk_amount)+
                                            chunk_amount],
                          iterations, results_queue, True, unsupervised))
                    for process_num in range(num_processes-1)]
    # start the processes
    for job in jobs: job.start()

    # while those processes are running, perform this process's work as well
    #    -Note: this process counts as one of the processes, so set to the
    #        last process number possible
    #    -Note: no need to copy this network onto the Queue (that would be
    #        redundant
    start_index = int((num_processes-1)*chunk_amount)
    _parallel_train_worker(network, trainer,
                           training_examples[start_index:
                                             start_index+chunk_amount],
                           iterations, results_queue, False, unsupervised)

    # retrieve the trained networks as they come in
    #    -Note: this is necessary because the multiprocess Queue is actually
    #        a pipe, and has a maximum size limit.  Therefore, it will not work
    #        unless these are pulled from the other end
    #    -Note: the get() will, by default, wait until there is an item ready
    #        with no timeout
    trained_networks = [results_queue.get() for _ in range(num_processes-1)]

    # now wait for the other processes to finish
    for job in jobs: job.join()

    # now average out the training networks into the master network
    #    by averaging the weights and threshold values
    for l, layer in enumerate(network.layers):
        for j, neuron in enumerate(layer.neurons):
            # average out weights
            for ij in range(len(neuron.weights)):
                weight_sum = 0.0
                for trained_network in trained_networks:
                    weight_sum += trained_network.layers[l].neurons[j].weights[ij]
                neuron.weights[ij] = (neuron.weights[ij]+weight_sum)/(len(trained_networks)+1)
            # average out thresholds
            threshold_sum = 0.0
            for trained_network in trained_networks:
                    threshold_sum += trained_network.layers[l].neurons[j].threshold
            neuron.threshold = (neuron.threshold+threshold_sum)/(len(trained_networks)+1)


def _parallel_train_worker(network, trainer, training_examples,
                           iterations, results_queue,
                           return_results_on_queue=True, unsupervised=False):
    """This private function is run by a parallel process to train the
    network on a given subset of the training data

    Note: Only processes OTHER than the main one will want to return the
        resulting network in the queue.  The main process will just be
        editing its network

    """
    trainer.train(network, training_examples, iterations, unsupervised)
    if return_results_on_queue:
        # return this trained network back to the main process by placing it on
        #    the queue
        results_queue.put(network)


def sign(x):
    """Return the sign (-1, 0, 1) of x"""
    if x < 0.0:
        sign = -1
    elif x == 0.0:
        sign = 0
    elif x > 0.0:
        sign = 1
    return sign