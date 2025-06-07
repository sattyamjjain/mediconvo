#!/usr/bin/env python3
"""
Mediconvo Demo - Interactive demonstration of the Agno-powered voice assistant
"""
import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from src.orchestration.command_processor import CommandProcessor
from src.utils.metrics import performance_metrics
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()


async def print_header():
    """Print demo header"""
    print("\n" + "=" * 80)
    print("🏥 Mediconvo Voice Assistant Demo - Powered by Agno AI Agents")
    print("=" * 80)
    print("A next-generation voice-activated EMR system for healthcare providers")
    print("Built with Agno framework for ultra-fast, intelligent agent coordination")
    print("=" * 80 + "\n")


async def demo_simple_commands(processor: CommandProcessor):
    """Demo simple single-agent commands"""
    print("\n📋 === Simple Commands Demo ===")
    print("Testing individual agent capabilities...\n")

    simple_commands = [
        ("Chart Agent", "Search for patients named Johnson"),
        ("Chart Agent", "Open chart for patient ID 12345"),
        ("Order Agent", "Order a CBC for the current patient"),
        ("Order Agent", "Prescribe metformin 500mg twice daily"),
        ("Messaging Agent", "Send appointment reminder to patient"),
        ("Messaging Agent", "Refer patient to cardiology for chest pain"),
    ]

    for expected_agent, command in simple_commands:
        print(f'🎤 Command: "{command}"')
        print(f"   Expected: {expected_agent}")

        try:
            response = await processor.process_voice_command(command)
            routing = response.data.get("routing", {})

            print(f"   ✅ Success: {response.success}")
            print(f"   🤖 Routed to: {routing.get('agent', 'Unknown')}")
            print(f"   📝 Response: {response.message[:100]}...")
            print()

        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()

        await asyncio.sleep(0.5)  # Brief pause between commands


async def demo_complex_workflows(processor: CommandProcessor):
    """Demo complex multi-agent workflows"""
    print("\n🔄 === Complex Multi-Agent Workflows Demo ===")
    print("Testing coordinated agent teamwork...\n")

    complex_commands = [
        "Find patient Smith, open their chart, and order a lipid panel",
        "Search for patient 12345, create a CBC order, and send them a notification about the lab work",
        "Open chart for Johnson, prescribe lisinopril 10mg daily, and send medication instructions",
        "Find patient Doe, create an urgent cardiology referral, and notify them about the appointment",
    ]

    for command in complex_commands:
        print(f'🎤 Complex Command: "{command}"')

        try:
            start_time = asyncio.get_event_loop().time()
            response = await processor.process_voice_command(command)
            execution_time = asyncio.get_event_loop().time() - start_time

            routing = response.data.get("routing", {})

            print(f"   ✅ Success: {response.success}")
            print(f"   🤖 Routing: {routing.get('agent', 'Unknown')}")
            print(f"   📊 Workflow: {routing.get('workflow', [])}")
            print(f"   ⏱️  Execution Time: {execution_time:.2f}s")
            print(f"   📝 Response: {response.message[:150]}...")
            print()

        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()

        await asyncio.sleep(1)  # Pause between complex commands


async def demo_performance_test(processor: CommandProcessor):
    """Demo performance characteristics"""
    print("\n⚡ === Performance Test Demo ===")
    print("Measuring Agno's ultra-fast agent performance...\n")

    test_commands = [
        "Search for patient test",
        "Order CBC",
        "Send message to patient",
        "Open chart for 123",
    ]

    # Warm-up run
    print("Warming up agents...")
    for cmd in test_commands:
        await processor.process_voice_command(cmd)

    # Performance test
    print("\nRunning performance test (3 iterations)...")

    for iteration in range(3):
        print(f"\n  Iteration {iteration + 1}:")
        iteration_times = []

        for cmd in test_commands:
            start = asyncio.get_event_loop().time()
            response = await processor.process_voice_command(cmd)
            duration = asyncio.get_event_loop().time() - start
            iteration_times.append(duration)

            status = "✅" if response.success else "❌"
            print(f"    {cmd:<40} → {duration:.3f}s {status}")

        avg_time = sum(iteration_times) / len(iteration_times)
        print(f"  Average: {avg_time:.3f}s")

    # Show metrics
    stats = performance_metrics.get_stats()
    print(f"\n📊 Overall Statistics:")
    print(f"   Total operations: {stats.get('total_operations', 0)}")

    if "operations" in stats:
        for op_name, op_stats in stats["operations"].items():
            print(f"   {op_name}:")
            print(f"     - Count: {op_stats['count']}")
            print(f"     - Average: {op_stats['average_duration']:.3f}s")
            print(f"     - Min: {op_stats['min_duration']:.3f}s")
            print(f"     - Max: {op_stats['max_duration']:.3f}s")


async def interactive_demo(processor: CommandProcessor):
    """Interactive command demo"""
    print("\n🎮 === Interactive Demo ===")
    print("Enter voice commands to test the system")
    print("Commands: 'help' for examples, 'metrics' for stats, 'quit' to exit\n")

    while True:
        try:
            command = input("🎤 Enter command: ").strip()

            if command.lower() in ["quit", "exit", "q"]:
                print("👋 Exiting interactive demo")
                break

            elif command.lower() == "help":
                help_text = await processor.get_help()
                print(f"\n{help_text}\n")
                continue

            elif command.lower() == "metrics":
                stats = performance_metrics.get_stats()
                print(f"\n📊 Performance Metrics:")
                print(json.dumps(stats, indent=2))
                print()
                continue

            elif command.lower() == "clear":
                performance_metrics.clear_metrics()
                print("✅ Metrics cleared\n")
                continue

            elif not command:
                continue

            # Process command
            print(f'\n🔄 Processing: "{command}"')

            start_time = asyncio.get_event_loop().time()
            response = await processor.process_voice_command(command)
            execution_time = asyncio.get_event_loop().time() - start_time

            # Display results
            print(f"\n✅ Success: {response.success}")

            if response.data.get("routing"):
                routing = response.data["routing"]
                print(f"🤖 Agent: {routing.get('agent', 'Unknown')}")
                print(f"🎯 Confidence: {routing.get('confidence', 0):.1%}")
                print(f"💭 Reasoning: {routing.get('reasoning', 'N/A')}")

            print(f"⏱️  Time: {execution_time:.3f}s")
            print(f"\n📝 Response:\n{response.message}\n")

        except KeyboardInterrupt:
            print("\n👋 Interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            logger.error(f"Interactive demo error: {e}", exc_info=True)


async def main():
    """Main demo function"""
    await print_header()

    # Validate environment
    model_provider = os.getenv("MODEL_PROVIDER", "openai")

    if model_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment")
        print("Please set your OpenAI API key in the .env file")
        return
    elif model_provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY not found in environment")
        print("Please set your Anthropic API key in the .env file")
        return

    print(f"🤖 Initializing Agno agents with {model_provider}...")

    try:
        # Initialize command processor
        processor = CommandProcessor(model_provider)

        # Show registered agents
        agents = processor.get_registered_agents()
        capabilities = processor.get_agent_capabilities()

        print(f"✅ Initialized successfully!")
        print(f"📋 Registered agents: {', '.join(agents)}")
        print(
            f"🔧 Total capabilities: {sum(len(caps) for caps in capabilities.values())}"
        )

        # Run demos
        await demo_simple_commands(processor)
        await demo_complex_workflows(processor)
        await demo_performance_test(processor)
        await interactive_demo(processor)

        # Export metrics
        print("\n📊 Exporting performance metrics...")
        filename = f"demo_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        performance_metrics.export_metrics(filename)
        print(f"✅ Metrics exported to {filename}")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.error(f"Demo error: {e}", exc_info=True)

    print("\n🎉 Demo completed!")
    print("Thank you for exploring Mediconvo with Agno AI Agents!")


if __name__ == "__main__":
    asyncio.run(main())
