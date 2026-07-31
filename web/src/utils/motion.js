import { h, defineComponent, withDirectives, resolveDirective } from "vue";
import { usePreferredReducedMotion } from "@vueuse/core";

/** 封装@vueuse/motion动画库中的自定义指令v-motion */
export default defineComponent({
  name: "Motion",
  props: {
    delay: {
      type: Number,
      default: 50,
    },
  },
  setup() {
    return {
      reducedMotion: usePreferredReducedMotion(),
    };
  },
  render() {
    const { delay } = this;
    const motion = resolveDirective("motion");
    return withDirectives(
      h(
        "div",
        {},
        {
          default: () => [this.$slots.default()],
        }
      ),
      [
        [
          motion,
          this.reducedMotion === "reduce"
            ? {
                initial: { opacity: 1, y: 0 },
                enter: { opacity: 1, y: 0 },
              }
            : {
                initial: { opacity: 0, y: 12 },
                enter: {
                  opacity: 1,
                  y: 0,
                  transition: {
                    delay,
                    duration: 240,
                    ease: [0.22, 1, 0.36, 1],
                  },
                },
              },
        ],
      ]
    );
  },
});
