package com.shangui.userhelp.order.mapper;

import com.shangui.userhelp.order.domain.Order;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

@Repository
public class MockOrderMapper implements OrderMapper {

    private static final String[] PRODUCTS = {"智能猫砂盆", "猫粮 5kg", "猫爬架", "自动饮水机"};
    private static final String[] STATUSES = {"待付款", "已付款", "已发货", "已签收"};

    @Override
    public Order findByOrderId(String orderId) {
        if (orderId == null || orderId.isBlank()) {
            return null;
        }
        Random random = new Random(("order:" + orderId).hashCode());
        String userId = isDemoOrder(orderId) ? null : "u" + Math.abs(orderId.hashCode() % 3 + 1);
        String status = demoStatus(orderId, random);
        String trackingNo = "SF" + (10000000000L + random.nextInt(899999999));
        return new Order(orderId, userId, status, 50 + random.nextInt(1951),
                LocalDate.of(2026, 7, 1 + random.nextInt(12)) + " 10:00",
                PRODUCTS[random.nextInt(PRODUCTS.length)], trackingNo);
    }

    @Override
    public List<Order> findByUserId(String userId) {
        List<Order> orders = new ArrayList<>();
        orders.add(withOwner(findByOrderId("1001"), userId));
        orders.add(withOwner(findByOrderId("2002"), userId));
        Random random = new Random(("user_orders:" + userId).hashCode());
        for (int i = 0; i < 2 + random.nextInt(3); i++) {
            String orderId = String.valueOf(3000 + random.nextInt(6000));
            orders.add(withOwner(findByOrderId(orderId), userId));
        }
        return orders;
    }

    private boolean isDemoOrder(String orderId) {
        return "1001".equals(orderId) || "2002".equals(orderId);
    }

    private String demoStatus(String orderId, Random random) {
        if ("1001".equals(orderId)) {
            return "已付款";
        }
        if ("2002".equals(orderId)) {
            return "已发货";
        }
        return STATUSES[random.nextInt(STATUSES.length)];
    }

    private Order withOwner(Order order, String userId) {
        return new Order(order.orderId(), userId, order.status(), order.amount(), order.createdAt(),
                order.product(), order.trackingNo());
    }
}
