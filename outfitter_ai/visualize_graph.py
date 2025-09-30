import os
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from main import OutfitterAssistant

def visualize_graph():
    assistant = OutfitterAssistant()
    assistant.setup_graph()
    
    try:
        # Get the graph object
        graph = assistant.graph.get_graph()
        
        print("\n" + "="*60)
        print("GRAPH STRUCTURE ANALYSIS")
        print("="*60)
        
        # Print all nodes
        print("\nNODES:")
        for node_id in graph.nodes:
            print(f"  • {node_id}")
        
        # Print all edges
        print("\nEDGES (Direct connections):")
        for start, end in graph.edges:
            print(f"  {start} → {end}")
        
        # Print conditional edges (these are the routing functions)
        print("\nCONDITIONAL EDGES (Routing logic):")
        
        # Access the internal graph structure
        if hasattr(assistant.graph, 'builder') and hasattr(assistant.graph.builder, 'branches'):
            branches = assistant.graph.builder.branches
            for source, branch_list in branches.items():
                print(f"\n  From '{source}':")
                for branch in branch_list:
                    if hasattr(branch, 'ends'):
                        ends = branch.ends if isinstance(branch.ends, dict) else {}
                        for condition, target in ends.items():
                            print(f"    → {condition}: '{target}'")
        
        # Try to generate Mermaid diagram using correct method
        print("\n" + "="*60)
        print("MERMAID DIAGRAM")
        print("="*60)
        
        try:
            # Newer LangGraph API
            from langgraph.graph import CompiledGraph
            
            # Generate mermaid string manually
            mermaid_lines = ["graph TD"]
            
            # Add nodes
            for node in graph.nodes:
                safe_id = node.replace("-", "_").replace(" ", "_")
                mermaid_lines.append(f"    {safe_id}[\"{node}\"]")
            
            # Add direct edges
            for start, end in graph.edges:
                safe_start = start.replace("-", "_").replace(" ", "_")
                safe_end = end.replace("-", "_").replace(" ", "_")
                mermaid_lines.append(f"    {safe_start} --> {safe_end}")
            
            # Add conditional edges
            conditional_mappings = {
                "intent_classifier": ["greeter", "needs_analyzer", "selection_handler", "checkout_handler", "general_responder", "clarification_asker"],
                "greeter": ["needs_analyzer", "wait_for_user"],
                "needs_analyzer": ["parallel_searcher", "clarification_asker"],
                "parallel_searcher": ["product_presenter", "clarification_asker", "general_responder"],
                "clarification_asker": ["needs_analyzer", "wait_for_user"]
            }
            
            for source, targets in conditional_mappings.items():
                safe_source = source.replace("-", "_").replace(" ", "_")
                for target in targets:
                    if target != "wait_for_user":  # Skip END connections
                        safe_target = target.replace("-", "_").replace(" ", "_")
                        mermaid_lines.append(f"    {safe_source} -.->|conditional| {safe_target}")
            
            mermaid_diagram = "\n".join(mermaid_lines)
            print(mermaid_diagram)
            print("\n📋 Copy the above and paste into https://mermaid.live")
            
        except Exception as e:
            print(f"⚠️ Could not generate Mermaid: {e}")
        
        # Analyze for cycles
        print("\n" + "="*60)
        print("CYCLE DETECTION")
        print("="*60)
        
        print("\n🔍 Looking for potential infinite loops...")
        
        # Check if clarification_asker connects back to needs_analyzer
        if ("clarification_asker", "needs_analyzer") in graph.edges:
            print("❌ CYCLE FOUND: clarification_asker → needs_analyzer")
            print("   This creates an infinite loop!")
        
        # Check if needs_analyzer connects back to clarification_asker
        if ("needs_analyzer", "clarification_asker") in graph.edges:
            print("⚠️ POTENTIAL CYCLE: needs_analyzer → clarification_asker")
            print("   This is OK only if clarification_asker ends at 'wait_for_user'")
        
        # Check for nodes without END connections
        end_nodes = ["product_presenter", "general_responder", "selection_handler", "checkout_handler"]
        print("\n📌 Checking END connections:")
        for node in end_nodes:
            has_end = any(end == "__end__" for start, end in graph.edges if start == node)
            if has_end:
                print(f"   ✅ {node} → END")
            else:
                print(f"   ❌ {node} missing END connection")
        
    except Exception as e:
        print(f"❌ Visualization error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    visualize_graph()