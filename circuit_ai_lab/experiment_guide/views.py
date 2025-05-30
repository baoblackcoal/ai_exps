import json
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views import View
from django.middleware.csrf import get_token # Required for CSRF token in context if not using {% csrf_token %} in a Django form

# Experiment step definitions (corresponds to Alpine's assistantPanelComponent.steps)
EXPERIMENT_STEPS = {
    'initial': {'id': 0, 'title': 'Welcome'}, # A pseudo-step before preparation
    'preparation': {'id': 1, 'title': 'Experiment Preparation'},
    'add_input_components': {'id': 2, 'title': 'Add Input Components'},
    'add_logic_gates': {'id': 3, 'title': 'Add Logic Gates'},
    'connect_components': {'id': 4, 'title': 'Connect Components'},
    'simulate_verify': {'id': 5, 'title': 'Simulate and Verify'},
    'summarize_results': {'id': 6, 'title': 'Summarize Results'}
}

TRUTH_TABLE_EXPECTED = [
    {'a': 0, 'b': 0, 's': 0, 'c_out': 0},
    {'a': 0, 'b': 1, 's': 1, 'c_out': 0},
    {'a': 1, 'b': 0, 's': 1, 'c_out': 0},
    {'a': 1, 'b': 1, 's': 0, 'c_out': 1}
]

# Mock AI response logic with session and richer responses
def get_mock_ai_response(user_message, session):
    user_message_lower = user_message.lower()
    current_step_name = session.get('experiment_step', 'initial')
    current_truth_table_row_index = session.get('truth_table_row_index', 0)

    ai_message = f"I received: '{user_message}'. Current step: {current_step_name}."
    next_step_id = EXPERIMENT_STEPS[current_step_name]['id']
    next_step_machine_name = current_step_name
    logging_instruction = "Default logging instruction."
    truth_table_update = None

    if current_step_name == 'initial':
        ai_message = "Hello! Welcome to the interactive half-adder experiment. We'll build and test a half-adder circuit together. Are you ready to start with the preparation?"
        next_step_id = EXPERIMENT_STEPS['preparation']['id']
        next_step_machine_name = 'preparation'
        logging_instruction = "Please review the theory of a half-adder. Type 'ready' or 'yes' when you want to begin."
    
    elif current_step_name == 'preparation':
        if "yes" in user_message_lower or "ready" in user_message_lower:
            ai_message = "Great! First, you'll need to add two input components to your CircuitJS workspace. These will represent A and B."
            next_step_id = EXPERIMENT_STEPS['add_input_components']['id']
            next_step_machine_name = 'add_input_components'
            logging_instruction = "In CircuitJS, go to 'Draw > Inputs and Sources > Add Logic Input (2-terminal)'. Add two of these. Have you done that?"
        else:
            ai_message = "Okay, take your time to review the preparation materials. Let me know when you're ready by typing 'yes' or 'ready'."
            logging_instruction = "Review half-adder theory. Type 'ready' or 'yes' to proceed."

    elif current_step_name == 'add_input_components':
        if "done" in user_message_lower or "added" in user_message_lower or "yes" in user_message_lower:
            ai_message = "Excellent. Now, add an XOR gate and an AND gate. These are essential for the half-adder's logic."
            next_step_id = EXPERIMENT_STEPS['add_logic_gates']['id']
            next_step_machine_name = 'add_logic_gates'
            logging_instruction = "Find XOR and AND gates under 'Draw > Logic Gates > Combinational Logic'. Let me know when you've added them."
        else:
            ai_message = "Make sure you add two Logic Inputs. They will be your A and B. Type 'done' when ready."
            logging_instruction = "Add two 'Logic Input' components in CircuitJS."

    elif current_step_name == 'add_logic_gates':
        if "done" in user_message_lower or "added" in user_message_lower or "yes" in user_message_lower:
            ai_message = "Perfect. Next, connect the inputs A and B to both the XOR gate and the AND gate. The output of the XOR gate will be your Sum (S), and the output of the AND gate will be your Carry-out (C_out)."
            next_step_id = EXPERIMENT_STEPS['connect_components']['id']
            next_step_machine_name = 'connect_components'
            logging_instruction = "Wire up the components. Connect A and B to both gate inputs. Label the XOR output 'S' and AND output 'C_out' (optional but good practice). Type 'connected' or 'done' when finished."
        else:
            ai_message = "Ensure you have one XOR gate and one AND gate on your canvas. Type 'done' when they are added."
            logging_instruction = "Add one XOR gate and one AND gate."
            
    elif current_step_name == 'connect_components':
        if "connected" in user_message_lower or "done" in user_message_lower or "yes" in user_message_lower:
            ai_message = "Fantastic! Your half-adder should be ready for testing. We'll now verify its truth table. Let's start with A=0, B=0."
            next_step_id = EXPERIMENT_STEPS['simulate_verify']['id']
            next_step_machine_name = 'simulate_verify'
            session['truth_table_row_index'] = 0 # Start verification from the first row
            current_truth_table_row_index = 0
            expected = TRUTH_TABLE_EXPECTED[current_truth_table_row_index]
            logging_instruction = f"In CircuitJS, set input A to {expected['a']} and B to {expected['b']}. What values do you observe for S and C_out? Please respond in the format 'S=value, C=value' (e.g., S=0, C=1)."
        else:
            ai_message = "Please make sure all connections are correct: A and B to both XOR and AND inputs. Type 'connected' when ready."
            logging_instruction = "Connect A & B to both gates. XOR output is S, AND output is C_out."

    elif current_step_name == 'simulate_verify':
        expected = TRUTH_TABLE_EXPECTED[current_truth_table_row_index]
        # Try to parse "S=value, C=value"
        s_val, c_val = None, None
        if "s=" in user_message_lower and "c=" in user_message_lower:
            try:
                parts = user_message_lower.split(',')
                s_part = parts[0][parts[0].find('s=')+2:].strip()
                c_part = parts[1][parts[1].find('c=')+2:].strip()
                s_val = int(s_part)
                c_val = int(c_part)
            except ValueError:
                ai_message = "Sorry, I couldn't understand those values. Please use the format 'S=value, C=value', for example, 'S=0, C=1'."
                logging_instruction = f"For A={expected['a']}, B={expected['b']}, what are S and C_out? Use format: S=value, C=value."
        
        if s_val is not None and c_val is not None:
            truth_table_update = {'row_index': current_truth_table_row_index, 's': s_val, 'c_out': c_val}
            if s_val == expected['s'] and c_val == expected['c_out']:
                ai_message = f"Correct! For A={expected['a']}, B={expected['b']}, S={s_val} and C_out={c_val} is right."
                current_truth_table_row_index += 1
                session['truth_table_row_index'] = current_truth_table_row_index
                if current_truth_table_row_index >= len(TRUTH_TABLE_EXPECTED):
                    ai_message += " You've successfully verified the entire truth table! The half-adder is working."
                    next_step_id = EXPERIMENT_STEPS['summarize_results']['id']
                    next_step_machine_name = 'summarize_results'
                    logging_instruction = "Congratulations! All checks passed. Let's summarize what we learned."
                else:
                    next_expected = TRUTH_TABLE_EXPECTED[current_truth_table_row_index]
                    ai_message += f" Now, let's try A={next_expected['a']}, B={next_expected['b']}."
                    logging_instruction = f"Set A to {next_expected['a']} and B to {next_expected['b']}. Report S and C_out using 'S=value, C=value'."
            else:
                ai_message = f"Hmm, for A={expected['a']}, B={expected['b']}, I expected S={expected['s']} and C_out={expected['c_out']}, but you reported S={s_val}, C_out={c_val}. Please double-check your circuit connections and the gate types."
                logging_instruction = f"Check circuit for A={expected['a']}, B={expected['b']}. Expected S={expected['s']}, C_out={expected['c_out']}. Then try again with 'S=value, C=value'."
        else: # If not 'S=value, C=value' format
            if not (s_val is None and c_val is None) : # Avoid repeating if parsing failed initially
                 ai_message = "Please use the format 'S=value, C=value' to report the outputs."
            logging_instruction = f"For A={expected['a']}, B={expected['b']}, what are S and C_out? Use format: S=value, C=value."


    elif current_step_name == 'summarize_results':
        ai_message = "This concludes the half-adder experiment. You've built it, tested it, and verified its behavior against its truth table. Well done!"
        logging_instruction = "Experiment complete! You can now try building a full adder, or ask me more questions about this circuit."
        # Optionally, reset step to 'initial' or a 'completed' state
        # session['experiment_step'] = 'initial' 
        # next_step_id = EXPERIMENT_STEPS['initial']['id']
        # next_step_machine_name = 'initial'


    # Fallback for unhandled messages within a step
    if ai_message.startswith("I received:"): # If no specific logic handled the message
        if current_step_name == 'preparation':
            logging_instruction = "Review half-adder theory. Type 'ready' or 'yes' to proceed."
        elif current_step_name == 'add_input_components':
            logging_instruction = "Add two 'Logic Input' components in CircuitJS. Type 'done' when ready."
        # ... add more specific fallback instructions for other steps
        else:
            logging_instruction = "I'm not sure how to respond to that in this step. Try following the current instructions."


    return {
        'ai_message': ai_message,
        'next_step_id': next_step_id,
        'next_step_machine_name': next_step_machine_name,
        'logging_instruction': logging_instruction,
        'truth_table_update': truth_table_update
    }

class IndexView(View):
    def get(self, request, *args, **kwargs):
        # Initialize session state if not present
        if 'experiment_step' not in request.session:
            request.session['experiment_step'] = 'initial'
        if 'truth_table_row_index' not in request.session: # Ensure this is also init'd
            request.session['truth_table_row_index'] = 0
        
        initial_step_name = request.session.get('experiment_step', 'initial')
        # Ensure initial_step_name is valid, fallback to 'initial' if session contains something unexpected
        initial_step_data = EXPERIMENT_STEPS.get(initial_step_name, EXPERIMENT_STEPS['initial'])

        initial_log_instruction = "Review the half-adder theory. Are you ready to start?" # Default for preparation
        if initial_step_name == 'initial':
            initial_log_instruction = "Hello! Welcome to the interactive half-adder experiment. Type 'hello' or 'ready' to get started with preparation."
        elif initial_step_name == 'add_input_components':
            initial_log_instruction = "In CircuitJS, go to 'Draw > Inputs and Sources > Add Logic Input (2-terminal)'. Add two of these. Have you done that?"
        # Add more else if blocks for other steps if needed, to ensure correct initial instructions on page refresh
        
        context = {
            'initial_step_id': initial_step_data['id'],
            'initial_logging_instruction': initial_log_instruction,
            # 'csrf_token': get_token(request) # Not needed due to {% csrf_token %}
        }
        return render(request, "experiment_guide/index.html", context)


class SendMessageView(View):
    def post(self, request, *args, **kwargs):
        user_message = request.POST.get('message', '')
        
        # Ensure session is started/available
        if not request.session.session_key:
            request.session.create()

        if 'experiment_step' not in request.session: # Initialize if somehow missed by IndexView
            request.session['experiment_step'] = 'initial'
            request.session['truth_table_row_index'] = 0

        response_data = get_mock_ai_response(user_message, request.session)
        
        # Update session state with the new step determined by get_mock_ai_response
        request.session['experiment_step'] = response_data['next_step_machine_name']
        # truth_table_row_index is updated within get_mock_ai_response if needed

        chat_html = render_to_string('experiment_guide/partials/ai_message.html', {'message_text': response_data['ai_message']})
        
        http_response = HttpResponse(chat_html)
        
        # Prepare data for HX-Trigger
        trigger_data = {
            "updateAssistantPanel": {
                "nextStepId": response_data['next_step_id'],
                "loggingInstruction": response_data['logging_instruction'],
                "truthTableUpdate": response_data['truth_table_update'] # This can be null
            }
        }
        http_response['HX-Trigger'] = json.dumps(trigger_data)
        
        return http_response
